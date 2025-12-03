"""Project management service."""

import logging
import re
from typing import Optional, List, Dict, Any

from domain.constants import HTTPStatus
from domain.exceptions import (
    ProjectCreationError,
    APIConnectionError,
    AuthenticationError,
)
from domain.models import Project, CollectionLogic
from domain.version import is_latest_version, get_latest_version
from services.connection import ConnectionService
from services.response_handler import APIResponseHandler

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing Dependency Track projects."""

    def __init__(self, connection_service: ConnectionService) -> None:
        self.connection = connection_service
        config = getattr(connection_service, "config", None)
        self.delete_on_suffix_match = (
            getattr(config, "delete_on_version_suffix_match", False)
            if config
            else False
        )
        configured_pattern = (
            getattr(config, "delete_version_suffix_pattern", "dev")
            if config
            else "dev"
        )
        self.delete_suffix_pattern = configured_pattern.strip() or "dev"

    def create_project(
        self,
        project: Project,
        auto_detect_latest: bool = True,
        delete_if_version_matches: Optional[bool] = None,
        delete_version_suffix_pattern: Optional[str] = None,
    ) -> Optional[Project]:
        """
        Create or update a project in Dependency Track.
        Args:
            project (Project): Project data to create or update
            auto_detect_latest (bool): Whether to auto-detect and set the latest version flag
        Returns:
            Optional[Project]: The created or updated project with UUID, or None if failed
        Raises:
            ProjectCreationError: If project creation fails
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        logger.info("Creating/updating project: %s", project.name)

        delete_on_suffix = (
            delete_if_version_matches
            if delete_if_version_matches is not None
            else self.delete_on_suffix_match
        )
        pattern = (
            delete_version_suffix_pattern.strip()
            if delete_version_suffix_pattern is not None
            else self.delete_suffix_pattern
        ) or None

        if self.connection.dry_run:
            logger.info("[DRY RUN] Would create project: %s", project.name)
            # Return a mock project with UUID for dry run
            project.uuid = "dry-run-uuid"
            if auto_detect_latest and project.version:
                self._handle_latest_version_detection(project, dry_run=True)
            return project

        # Check if project exists
        existing_project = self._find_existing_project(project.name, project.version)

        if existing_project:
            logger.info("Project already exists: %s", existing_project["uuid"])
            project.uuid = existing_project["uuid"]

            # Handle latest version detection before updating
            if auto_detect_latest and project.version:
                self._handle_latest_version_detection(
                    project, 
                    delete_on_suffix=delete_on_suffix,
                    delete_pattern=pattern
                )

            # Update the existing project with new properties
            return self._update_project(project)

        # Create new project
        try:
            logger.debug("Sending PUT request to create project: %s", project.name)
            response = self.connection.make_request(
                method="PUT", endpoint="/project", json=project.to_api_dict()
            )
            logger.debug("Received response for project creation: %s (type: %s)", 
                        project.name, type(response).__name__)
        except APIConnectionError as conn_err:
            # Re-raise connection errors as ProjectCreationError with context
            raise ProjectCreationError(
                f"Failed to create project {project.name}: {conn_err}"
            ) from conn_err
        except Exception as exc:
            # Catch any unexpected exceptions
            logger.error("Unexpected error during project creation for %s: %s", 
                        project.name, exc, exc_info=True)
            raise ProjectCreationError(
                f"Unexpected error creating project {project.name}: {exc}"
            ) from exc

        # Check response validity and handle special status codes
        if response is None:
            logger.error("Response is None for project: %s (dry_run: %s)", 
                       project.name, self.connection.dry_run)
            raise ProjectCreationError(f"No response received for project {project.name}")
        
        # Handle 409 Conflict - project already exists with same name
        if response.status_code == HTTPStatus.CONFLICT.value:
            logger.warning("Project %s (version: %s) already exists (409 Conflict), treating as existing project", 
                         project.name, project.version)
            
            # First try to find with exact version match
            existing_project = self._find_existing_project(project.name, project.version)
            
            # If not found with exact version, try without version constraint
            # (409 means a project with this name exists, possibly with different version)
            if not existing_project:
                logger.info("Exact version not found, searching for any project with name: %s", project.name)
                existing_project = self._find_existing_project(project.name, None)
            
            if existing_project:
                project.uuid = existing_project["uuid"]
                logger.info("Found existing project: %s (existing version: %s, new version: %s)", 
                          project.uuid, existing_project.get("version"), project.version)
                
                #Handle latest version detection
                if auto_detect_latest and project.version:
                    self._handle_latest_version_detection(project)
                
                # Update the existing project (this will update the version if it changed)
                return self._update_project(project)
            else:
                # Try to parse the response to get more info about the conflict
                try:
                    if response.text:
                        logger.error("409 response body: %s", response.text)
                except Exception:
                    pass
                raise ProjectCreationError(
                    f"Project {project.name} (version: {project.version}) exists (409 Conflict) but could not be retrieved. "
                    f"This may indicate a database inconsistency."
                )
        
        try:
            project_data = APIResponseHandler.handle_response(
                response,
                success_status=HTTPStatus.CREATED,
                operation="Project creation",
            )
            project.uuid = project_data["uuid"]
            logger.info("Project created: %s", project.uuid)

            # Handle latest version detection after creation
            if auto_detect_latest and project.version:
                self._handle_latest_version_detection(
                    project,
                    delete_on_suffix=delete_on_suffix,
                    delete_pattern=pattern
                )
                # Update the project if latest flag changed
                if project.is_latest:
                    self._update_project(project)

            return project

        except APIConnectionError as error:
            raise ProjectCreationError(
                f"Failed to create project {project.name}: {error}"
            ) from error

    def _should_delete_project(
        self,
        version: Optional[str],
        delete_on_suffix: bool,
        pattern: Optional[str],
        collection_logic: CollectionLogic = CollectionLogic.NONE,
    ) -> bool:
        """Determine whether existing project should be deleted based on version pattern.
        
        Args:
            version: Project version string
            delete_on_suffix: Whether suffix-based deletion is enabled
            pattern: Regex pattern for matching version suffix
            collection_logic: Project collection logic (skip deletion if not NONE)
            
        Returns:
            True if project should be deleted, False otherwise
        """
        if not delete_on_suffix:
            return False
        if collection_logic != CollectionLogic.NONE:
            logger.debug("Skipping deletion for collection project (logic: %s)", collection_logic)
            return False
        if not version or not pattern:
            return False

        return self._matches_delete_pattern(version, pattern)

    def _matches_delete_pattern(self, version: str, pattern: str) -> bool:
        """Check whether the version matches the configured deletion pattern."""
        try:
            return bool(re.search(pattern, version, re.IGNORECASE))
        except re.error:
            logger.warning(
                "Invalid delete version suffix pattern '%s'; falling back to substring match",
                pattern,
            )
            return pattern.lower() in version.lower()

    def _delete_project(
        self,
        project_uuid: Optional[str],
        project_name: str,
        project_version: Optional[str],
    ) -> bool:
        """Delete an existing project by UUID.
        
        Args:
            project_uuid: UUID of project to delete
            project_name: Name of project (for logging)
            project_version: Version of project (for logging)
            
        Returns:
            True if deletion succeeded or project already absent, False on failure
        """
        if not project_uuid:
            logger.warning(
                "Cannot delete project %s %s: missing project UUID",
                project_name,
                project_version,
            )
            return False

        if self.connection.dry_run:
            logger.info(
                "[DRY RUN] Would delete project %s (version: %s, uuid: %s)",
                project_name,
                project_version,
                project_uuid,
            )
            return True

        response = self.connection.make_request(
            method="DELETE", endpoint=f"/project/{project_uuid}"
        )

        if response is None:
            # Request suppressed (e.g., dry run handled upstream)
            return True

        if response.status_code in (
            HTTPStatus.NO_CONTENT.value,
            HTTPStatus.OK.value,
        ):
            logger.info(
                "Deleted project %s (version: %s, uuid: %s)",
                project_name,
                project_version,
                project_uuid,
            )
            return True

        if response.status_code == 404:
            logger.info(
                "Project %s (version: %s) already absent during delete attempt",
                project_name,
                project_version,
            )
            return True

        try:
            response_text = response.text  # type: ignore[attr-defined]
        except Exception:  # pylint: disable=broad-except
            response_text = "<no response body>"

        logger.warning(
            "Failed to delete project %s (version: %s, uuid: %s): status %s - %s",
            project_name,
            project_version,
            project_uuid,
            response.status_code,
            response_text,
        )
        return False

    def _update_project(self, project: Project) -> Optional[Project]:
        """
        Update an existing project with new properties.
        Args:
            project (Project): Project data with updated properties
        Returns:
            Optional[Project]: The updated project, or None if update failed
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        if self.connection.dry_run:
            logger.info("[DRY RUN] Would update project: %s", project.name)
            return project

        response = self.connection.make_request(
            method="PATCH",
            endpoint=f"/project/{project.uuid}",
            json=project.to_api_dict(),
        )

        try:
            APIResponseHandler.handle_response(
                response, success_status=HTTPStatus.OK, operation="Project update"
            )
            logger.info("Project updated: %s", project.uuid)
        except APIConnectionError:
            logger.warning(
                "Failed to update project %s: API error occurred",
                project.name,
            )
            # Continue anyway since the project exists

        return project

    def _find_existing_project(
        self, name: str, version: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Find an existing project by name and version.
        Args:
            name (str): Project name
            version (Optional[str]): Project version, or None to ignore version
        Returns:
            Optional[Dict[str, Any]]: The existing project data if found, else None
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        # Use lookup endpoint to search by name with pagination support
        # DependencyTrack supports /api/v1/project/lookup?name=X&version=Y
        endpoint = f"/project/lookup?name={name}"
        if version:
            endpoint += f"&version={version}"
        
        response = self.connection.make_request(method="GET", endpoint=endpoint)
        
        try:
            project = APIResponseHandler.handle_response(
                response, success_status=HTTPStatus.OK, operation="Project lookup"
            )
            if project:
                logger.debug("Found project via lookup: %s (uuid: %s)", 
                           project.get("name"), project.get("uuid"))
                return project
            return None
        except APIConnectionError:
            logger.debug("Project lookup failed, falling back to list endpoint")
            # Fall back to listing all projects if lookup fails
            pass
        
        # Fallback: list all projects (with pagination)
        response = self.connection.make_request(method="GET", endpoint="/project")

        try:
            projects = APIResponseHandler.handle_response(
                response, success_status=HTTPStatus.OK, operation="Get projects"
            )
            if not projects:
                return None

            logger.debug("Searching for project: name='%s', version='%s'", name, version)
            logger.debug("Total projects in response: %d", len(projects))
            
            # Check if we're looking for veeam-exporter to debug
            if "veeam" in name.lower():
                veeam_projects = [p for p in projects if "veeam" in p["name"].lower()]
                logger.debug("Found %d projects with 'veeam' in name: %s", 
                           len(veeam_projects), 
                           [(p["name"], p.get("version")) for p in veeam_projects])
            
            for project in projects:
                if project["name"] == name:
                    logger.debug("Found matching name: %s (version: %s)", 
                               project["name"], project.get("version"))
                    if version is None or project.get("version") == version:
                        return project
                    else:
                        logger.debug("Version mismatch: looking for '%s', found '%s'", 
                                   version, project.get("version"))

            logger.debug("No matching project found")
            return None
        except APIConnectionError:
            logger.warning("Failed to retrieve projects for lookup")
            return None

    def get_project_hierarchy(
        self, project_uuid: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get project hierarchy information.
        Args:
            project_uuid (Optional[str]):
                Specific project UUID to get hierarchy for, or None for all
        Returns:
            List[Dict[str, Any]]: List of projects with hierarchy information
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        if project_uuid:
            return self._get_single_project_hierarchy(project_uuid)

        return self._get_all_projects_hierarchy()

    def _get_single_project_hierarchy(self, project_uuid: str) -> List[Dict[str, Any]]:
        """
        Get hierarchy for a specific project.
        Args:
            project_uuid (str): UUID of the project to get hierarchy for
        Returns:
            List[Dict[str, Any]]: List containing the project and its children
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        # Get project details
        response = self.connection.make_request(
            method="GET", endpoint=f"/project/{project_uuid}"
        )

        if not response or response.status_code != 200:
            return []

        project = response.json()
        result = [project]

        # Get children
        children_response = self.connection.make_request(
            method="GET", endpoint=f"/project/{project_uuid}/children"
        )

        if children_response and children_response.status_code == 200:
            project["children"] = children_response.json()
        else:
            project["children"] = []

        return result

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects from Dependency Track.
        Args:
            None
        Returns:
            List[Dict[str, Any]]: List of all projects
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        try:
            response = self.connection.make_request(
                method="GET", endpoint="/project", params={"excludeInactive": "true"}
            )

            projects = APIResponseHandler.handle_response(
                response, success_status=HTTPStatus.OK, operation="Get all projects"
            )

            return projects if isinstance(projects, list) else []

        except (APIConnectionError, AuthenticationError) as error:
            logger.error("Error getting all projects: %s", error)
            raise

    def _get_all_projects_hierarchy(self) -> List[Dict[str, Any]]:
        """
        Get hierarchy for all projects.
        Args:
            None
        Returns:
            List[Dict[str, Any]]: List of all projects with their hierarchy
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
        """
        response = self.connection.make_request(method="GET", endpoint="/project")

        if not response or response.status_code != 200:
            return []

        projects = response.json()

        # Find root projects (those without parents)
        root_projects = [p for p in projects if not p.get("parent")]

        # For each root project, get its children
        for root in root_projects:
            children_response = self.connection.make_request(
                method="GET", endpoint=f"/project/{root['uuid']}/children"
            )

            root["children"] = []
            if children_response and children_response.status_code == 200:
                root["children"] = children_response.json()

        return root_projects

    def _handle_latest_version_detection(
        self,
        project: Project,
        dry_run: bool = False,
        delete_on_suffix: bool = False,
        delete_pattern: Optional[str] = None,
    ) -> None:
        """
        Automatically detect if this project version should be marked as latest.
        This method:
            1. Gets all versions of the same project name
            2. Determines if the current version is the latest
            3. Updates latest flags accordingly
            4. If parent has deletion pattern, deletes superseded versions
        Args:
            project (Project): The project to evaluate and potentially update
            dry_run (bool): If True, simulate without making changes
            delete_on_suffix (bool): Whether to delete old versions based on parent pattern
            delete_pattern (Optional[str]): Pattern to check against parent version
        Returns:
            None
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            ValueError: If version comparison fails
            TypeError: If version data is invalid
        """
        if not project.version:
            return

        if dry_run:
            logger.info(
                "[DRY RUN] Would check if %s %s is latest",
                project.name,
                project.version,
            )
            return

        try:
            all_projects = self._get_all_versions_of_project(project.name)
        except (
            APIConnectionError,
            AuthenticationError,
            ValueError,
            TypeError,
        ) as error:
            logger.warning("Failed to get all versions for %s: %s", project.name, error)
            return

        if not all_projects:
            # If no other versions exist, this is the latest
            project.is_latest = True
            logger.info(
                "%s %s is the first version - marking as latest",
                project.name,
                project.version,
            )
            return

        # Extract all version strings
        version_strings = []
        project_version_map = {}

        try:
            for proj in all_projects:
                if proj.get("version"):
                    version_strings.append(proj["version"])
                    project_version_map[proj["version"]] = proj

        except KeyError as error:
            logger.warning("Error processing versions for %s: %s", project.name, error)
            return

        # Add current version if not already in list
        if project.version not in version_strings:
            version_strings.append(project.version)

        try:
            # Determine if current version is latest
            current_is_latest = is_latest_version(project.version, version_strings)

        except ValueError as error:
            logger.warning(
                "Version comparison failed for %s %s: %s",
                project.name,
                project.version,
                error,
            )
            return

        if current_is_latest:
            project.is_latest = True
            logger.info("%s %s is the latest version", project.name, project.version)

            # Delete superseded versions if parent matches pattern
            delete_old = False
            if delete_on_suffix and delete_pattern:
                parent_version = self._get_parent_version(project)
                delete_old = (
                    parent_version and self._matches_delete_pattern(parent_version, delete_pattern)
                )

            self._update_latest_flags_for_project(
                project.name, project.version, all_projects, delete_old=delete_old
            )
        else:
            project.is_latest = False
            latest_version = get_latest_version(version_strings)
            logger.info(
                "%s %s is not latest (latest: %s)",
                project.name,
                project.version,
                latest_version,
            )

    def _get_all_versions_of_project(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all versions of a project by name."""
        response = self.connection.make_request(method="GET", endpoint="/project")

        if not response or response.status_code != 200:
            return []

        projects = response.json()
        return [p for p in projects if p["name"] == project_name]

    def _update_latest_flags_for_project(
        self,
        project_name: str,
        latest_version: str,
        all_projects: List[Dict[str, Any]],
        delete_old: bool = False,
    ) -> None:
        """
        Update latest flags for all versions of a project.
        Args:
            project_name (str): Name of the project
            latest_version (str): The version string that should be marked as latest
            all_projects (List[Dict[str, Any]]): List of all project versions
            delete_old (bool): If True, delete old latest versions instead of just removing flag
        """
        for proj in all_projects:
            if not proj.get("version") or proj["version"] == latest_version:
                continue
            if not proj.get("isLatest", False):
                continue

            if delete_old:
                logger.info(
                    "Deleting superseded version %s v%s (parent has deletion pattern)",
                    project_name,
                    proj["version"],
                )
                self._delete_project(proj["uuid"], project_name, proj["version"])
                continue

            logger.info("Removing latest flag from %s v%s", project_name, proj["version"])
            self._remove_latest_flag(proj["uuid"])

    def _get_parent_version(self, project: Project) -> Optional[str]:
        """
        Get the version of a project's parent.
        Args:
            project (Project): The project whose parent version to retrieve
        Returns:
            Optional[str]: Parent version string, or None if no parent or error
        """
        if not project.parent_uuid:
            return None

        try:
            response = self.connection.make_request(
                method="GET", endpoint=f"/project/{project.parent_uuid}"
            )
            if response and response.status_code == 200:
                parent_data = response.json()
                return parent_data.get("version")
        except (APIConnectionError, AuthenticationError, KeyError) as error:
            logger.debug("Failed to get parent version: %s", error)

        return None

    def _remove_latest_flag(self, project_uuid: str) -> None:
        """
        Remove the latest flag from a specific project.
        Args:
            project_uuid (str): UUID of the project to update
        Returns:
            None
        Raises:
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            KeyError: If expected data is missing
            TypeError: If data types are incorrect
        """
        try:
            # Get current project data
            response = self.connection.make_request(
                method="GET", endpoint=f"/project/{project_uuid}"
            )

            if response and response.status_code == 200:
                project_data = response.json()
                project_data["isLatest"] = False

                # Update the project
                update_response = self.connection.make_request(
                    method="PATCH",
                    endpoint=f"/project/{project_uuid}",
                    json=project_data,
                )

                if update_response and update_response.status_code == 200:
                    logger.info("Removed latest flag from project %s", project_uuid)
                else:
                    logger.warning(
                        "Failed to remove latest flag from project %s", project_uuid
                    )
        except (APIConnectionError, AuthenticationError, KeyError, TypeError) as error:
            logger.warning(
                "Error removing latest flag from project %s: %s", project_uuid, error
            )
