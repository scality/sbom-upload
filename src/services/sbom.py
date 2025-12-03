"""SBOM upload service."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
import yaml

from domain.constants import APIConstants, HTTPStatus
from domain.exceptions import (
    SBOMFileError,
    UploadError,
    APIConnectionError,
    AuthenticationError,
)
from domain.models import (
    SBOMFile,
    Project,
    UploadResult,
    HierarchyConfig,
    CollectionLogic,
    ProjectClassifier,
)
from services.connection import ConnectionService
from services.file_discovery import discover_sbom_files
from services.project import ProjectService
from services.response_handler import APIResponseHandler

logger = logging.getLogger(__name__)


class SBOMService:
    """Service for SBOM operations."""

    def __init__(
        self, connection_service: ConnectionService, project_service: ProjectService
    ) -> None:
        self.connection = connection_service
        self.project_service = project_service

    def _upload_sbom_file(
        self,
        sbom_file: SBOMFile,
        project_data: Optional[Dict[str, str]] = None,
        project_uuid: Optional[str] = None,
        operation_name: str = "SBOM upload",
    ) -> UploadResult:
        """
        Common SBOM file upload logic.
        Args:
            sbom_file (SBOMFile): The SBOM file to upload
            project_data (Optional[Dict[str, str]]): Data for project creation if needed
            project_uuid (Optional[str]): UUID of the existing project to upload to
            operation_name (str): Description of the operation for logging
        Returns:
            UploadResult: Result of the upload operation
        Raises:
            UploadError: If the upload fails
            APIConnectionError: If there is a connection issue
        """
        if self.connection.dry_run:
            target = project_uuid or "new project"
            return UploadResult.success_result(
                project_uuid=project_uuid or "dry-run-uuid",
                message=f"[DRY RUN] Would upload {sbom_file.path.name} to {target}",
            )

        try:
            with sbom_file.path.open("rb") as file_handle:
                # Prepare the files parameter
                files = {
                    "bom": (
                        sbom_file.path.name,
                        file_handle,
                        APIConstants.JSON_CONTENT_TYPE,
                    )
                }

                # Add project UUID if uploading to existing project
                if project_uuid:
                    files["project"] = (None, project_uuid)

                response = self.connection.make_request(
                    method="POST",
                    endpoint="/bom",
                    files=files,
                    data=project_data,
                )

            result_data = APIResponseHandler.handle_response(
                response, success_status=HTTPStatus.OK, operation=operation_name
            )

            return UploadResult.success_result(
                project_uuid=result_data.get("project", {}).get("uuid") or project_uuid,
                message="SBOM uploaded successfully",
                token=result_data.get("token"),
            )

        except APIConnectionError as error:
            return UploadResult.failure_result(
                f"Failed to upload SBOM {sbom_file.path.name}: {error}"
            )

    def upload_single_sbom(
        self, sbom_file: SBOMFile, project_name: str = None, project_version: str = None
    ) -> UploadResult:
        """
        Upload a single SBOM file with automatic project creation.
        Args:
            sbom_file (SBOMFile): The SBOM file to upload
            project_name (str): Optional project name to override SBOM metadata
            project_version (str): Optional project version to override SBOM metadata
        Returns:
            UploadResult: Result of the upload operation
        Raises:
            OSError: If there is a file access issue
            SBOMFileError: If there is an issue with the SBOM file
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            UploadError: If the upload fails
        """
        try:
            logger.info("Uploading SBOM: %s", sbom_file.path)

            # Load metadata from SBOM
            metadata = sbom_file.load_metadata()

            # Use provided values or fallback to SBOM metadata
            base_project_name = project_name or metadata.name
            final_project_name = self.connection.config.apply_name_transformations(
                base_project_name
            )
            final_project_version = project_version or metadata.version

            logger.info(
                "Project: %s, Version: %s", final_project_name, final_project_version
            )

            # Use common upload logic with auto-create data
            project_data = {
                "projectName": final_project_name,
                "projectVersion": final_project_version,
                "autoCreate": APIConstants.AUTO_CREATE_TRUE,
            }

            return self._upload_sbom_file(
                sbom_file=sbom_file,
                project_data=project_data,
                operation_name="SBOM upload with auto-create",
            )

        except (
            OSError,
            SBOMFileError,
            APIConnectionError,
            AuthenticationError,
            UploadError,
        ) as error:
            logger.error("Error uploading SBOM: %s", error)
            return UploadResult.failure_result(str(error))

    def upload_to_project(self, project_uuid: str, sbom_file: SBOMFile) -> UploadResult:
        """
        Upload SBOM to an existing project.
        Args:
            project_uuid (str): UUID of the existing project
            sbom_file (SBOMFile): The SBOM file to upload
        Returns:
            UploadResult: Result of the upload operation
        Raises:
            OSError: If there is a file access issue
            SBOMFileError: If there is an issue with the SBOM file
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            UploadError: If the upload fails
        """
        try:
            logger.info(
                "Uploading SBOM %s to project %s", sbom_file.path.name, project_uuid
            )

            return self._upload_sbom_file(
                sbom_file=sbom_file,
                project_uuid=project_uuid,
                operation_name="SBOM upload to project",
            )

        except (
            OSError,
            SBOMFileError,
            APIConnectionError,
            AuthenticationError,
            UploadError,
        ) as error:
            logger.error("Error uploading SBOM to project: %s", error)
            return UploadResult.failure_result(str(error))

    def upload_multiple_sboms(
        self,
        sbom_files: List[Path],
        project_name: str = None,
        project_version: str = None,
    ) -> List[UploadResult]:
        """
        Upload multiple SBOM files.
        Args:
            sbom_files (List[Path]): List of SBOM file paths to upload
            project_name (str): Optional project name to override SBOM metadata
            project_version (str): Optional project version to override SBOM metadata
        Returns:
            List[UploadResult]: List of results for each upload
        Raises:
            OSError: If there is a file access issue
            SBOMFileError: If there is an issue with any SBOM file
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            UploadError: If any upload fails
        """
        results = []

        for sbom_path in sbom_files:
            try:
                sbom_file = SBOMFile(path=sbom_path)
                result = self.upload_single_sbom(
                    sbom_file, project_name, project_version
                )
                results.append(result)
            except (
                OSError,
                SBOMFileError,
                APIConnectionError,
                AuthenticationError,
                UploadError,
            ) as error:
                logger.error("Error processing %s: %s", sbom_path, error)
                results.append(
                    UploadResult.failure_result(
                        f"Failed to process {sbom_path.name}: {error}"
                    )
                )

        return results

    def upload_nested_hierarchy(  # pylint: disable=too-many-locals, too-many-branches, too-many-positional-arguments, too-many-arguments
        self,
        parent_name: str,
        parent_version: str,
        sbom_dir: Path,
        parent_classifier: str = "APPLICATION",
        parent_collection_logic: str = "AGGREGATE_LATEST_VERSION_CHILDREN",
    ) -> UploadResult:
        """
        Upload multiple SBOMs as child projects under a parent project.
        Args:
            parent_name (str): Name of the parent project
            parent_version (str): Version of the parent project
            sbom_dir (Path): Directory containing SBOM files to upload as children
            parent_classifier (str): Classifier for the parent project
                (default: "APPLICATION")
            parent_collection_logic (str): Collection logic for the parent project
                (default: "AGGREGATE_LATEST_VERSION_CHILDREN")
        Returns:
            UploadResult: Result of the nested upload operation
        Raises:
            OSError: If there is a file access issue
            SBOMFileError: If there is an issue with any SBOM file
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            UploadError: If any upload fails
        """
        try:
            logger.info("Creating nested project structure for: %s", parent_name)

            # Find all JSON files in the directory
            sbom_files = discover_sbom_files(sbom_dir)
            if not sbom_files:
                return UploadResult.failure_result(
                    f"No JSON files found in: {sbom_dir}"
                )

            logger.info("Found %d SBOM files", len(sbom_files))

            # Create parent project
            parent_project = Project(
                name=parent_name,
                version=parent_version,
                classifier=ProjectClassifier(parent_classifier),
                collection_logic=CollectionLogic(parent_collection_logic),
            )

            created_parent = self.project_service.create_project(
                parent_project, auto_detect_latest=False
            )
            if not created_parent:
                return UploadResult.failure_result("Failed to create parent project")

            logger.info("Parent project created: %s", created_parent.uuid)

            # Process each SBOM file as a child project
            successful_uploads = 0
            failed_uploads = 0

            for sbom_path in sbom_files:
                try:
                    sbom_file = SBOMFile(path=sbom_path)
                    metadata = sbom_file.load_metadata()

                    # Create child project
                    child_project_name = (
                        self.connection.config.apply_name_transformations(metadata.name)
                    )
                    child_project = Project(
                        name=child_project_name,
                        version=metadata.version,
                        parent_uuid=created_parent.uuid,
                    )

                    created_child = self.project_service.create_project(
                        child_project, auto_detect_latest=True
                    )
                    if not created_child:
                        logger.error(
                            "Failed to create child project for %s", metadata.name
                        )
                        failed_uploads += 1
                        continue

                    # Upload SBOM to child project
                    upload_result = self.upload_to_project(
                        created_child.uuid, sbom_file
                    )

                    if upload_result.success:
                        logger.info("SBOM uploaded successfully: %s", sbom_path.name)
                        successful_uploads += 1
                        continue

                    logger.error("Failed to upload SBOM: %s", sbom_path.name)
                    failed_uploads += 1

                except (
                    OSError,
                    SBOMFileError,
                    APIConnectionError,
                    AuthenticationError,
                    UploadError,
                ) as error:
                    logger.error("Error processing %s: %s", sbom_path.name, error)
                    failed_uploads += 1

            success_msg = (
                f"Nested upload complete: {successful_uploads} successful,"
                f" {failed_uploads} failed"
            )
            if successful_uploads > 0:
                return UploadResult.success_result(created_parent.uuid, success_msg)

            return UploadResult.failure_result(success_msg)

        except (
            OSError,
            SBOMFileError,
            APIConnectionError,
            AuthenticationError,
            UploadError,
        ) as error:
            logger.error("Error in nested hierarchy upload: %s", error)
            return UploadResult.failure_result(str(error))

    def upload_from_hierarchy_config(self, config_file: Path) -> UploadResult:
        """
        Upload SBOMs using custom hierarchy configuration.
        Args:
            config_file (Path): Path to the JSON or YAML configuration file
        Returns:
            UploadResult: Result of the hierarchy upload operation
        Raises:
            OSError: If there is a file access issue
            FileNotFoundError: If the config file does not exist
            json.JSONDecodeError: If the config file is invalid JSON
            ValueError: If the config data is invalid
            KeyError: If required keys are missing in the config
        """
        try:
            logger.info("Creating custom hierarchy from: %s", config_file)

            # Load configuration
            with open(config_file, "r", encoding="utf-8") as f:
                if config_file.suffix.lower() in [".yaml", ".yml"]:
                    try:
                        config_data = yaml.safe_load(f)
                    except ImportError:
                        return UploadResult.failure_result(
                            "PyYAML not installed. Please use JSON format or install PyYAML."
                        )
                    except yaml.YAMLError as error:
                        return UploadResult.failure_result(
                            f"Invalid YAML format: {error}"
                        )
                else:
                    config_data = json.load(f)

            successful_uploads = 0
            failed_uploads = 0

            # Process the hierarchy recursively
            for root_name, root_config in config_data.items():
                result = self._process_hierarchy_project(root_name, root_config, None)
                if result.success:
                    successful_uploads += 1
                else:
                    failed_uploads += 1

            success_msg = (
                f"Hierarchy upload complete: {successful_uploads} successful,"
                f" {failed_uploads} failed"
            )
            if successful_uploads > 0:
                return UploadResult.success_result(None, success_msg)

            return UploadResult.failure_result(success_msg)

        except (
            OSError,
            FileNotFoundError,
            json.JSONDecodeError,
            ValueError,
            KeyError,
        ) as error:
            logger.error("Error loading hierarchy configuration: %s", error)
            return UploadResult.failure_result(str(error))

    def _process_hierarchy_project(
        self, project_name: str, project_config: Dict[str, Any], parent_uuid: str = None
    ) -> UploadResult:
        """
        Process a single project in the hierarchy configuration.
        Args:
            project_name (str): Name of the project
            project_config (Dict[str, Any]): Configuration dictionary for the project
            parent_uuid (str): UUID of the parent project, if any
        Returns:
            UploadResult: Result of processing this project
        Raises:
            OSError: If there is a file access issue
            SBOMFileError: If there is an issue with the SBOM file
            APIConnectionError: If there is a connection issue
            AuthenticationError: If authentication fails
            UploadError: If any upload fails
            KeyError: If required keys are missing in the config
            ValueError: If the config data is invalid
        """
        try:
            hierarchy_config = HierarchyConfig.from_dict(project_config)

            # Create the project
            project = Project(
                name=project_name,
                version=hierarchy_config.version,
                classifier=hierarchy_config.classifier,
                collection_logic=hierarchy_config.collection_logic,
                parent_uuid=parent_uuid,
                tags=hierarchy_config.tags,
                is_latest=hierarchy_config.is_latest,
            )

            created_project = self.project_service.create_project(
                project,
                auto_detect_latest=True,
                delete_if_version_matches=self.project_service.delete_on_suffix_match,
                delete_version_suffix_pattern=self.project_service.delete_suffix_pattern,
            )
            if not created_project:
                return UploadResult.failure_result(
                    f"Failed to create project: {project_name}"
                )

            # Upload SBOM if specified
            if hierarchy_config.sbom_file:
                sbom_path = Path(hierarchy_config.sbom_file)
                if sbom_path.exists():
                    sbom_file = SBOMFile(path=sbom_path)
                    upload_result = self.upload_to_project(
                        created_project.uuid, sbom_file
                    )

                    if not upload_result.success:
                        return UploadResult.failure_result(
                            f"Failed to upload SBOM for {project_name}"
                        )
                else:
                    logger.warning(
                        "SBOM file not found: %s", hierarchy_config.sbom_file
                    )

            # Process children
            for child_config in hierarchy_config.children:
                child_name = child_config.get("name")
                if child_name:
                    child_result = self._process_hierarchy_project(
                        child_name, child_config, created_project.uuid
                    )
                    if not child_result.success:
                        logger.error("Failed to process child project: %s", child_name)

            return UploadResult.success_result(
                created_project.uuid, f"Project {project_name} processed successfully"
            )

        except (
            OSError,
            SBOMFileError,
            APIConnectionError,
            AuthenticationError,
            UploadError,
            KeyError,
            ValueError,
        ) as error:
            logger.error(
                "Error processing hierarchy project %s: %s", project_name, error
            )
            return UploadResult.failure_result(str(error))
