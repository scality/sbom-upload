"""Domain models for the SBOM upload application."""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
from domain.exceptions import SBOMFileError


class ProjectClassifier(Enum):
    """Project classifier enum."""

    APPLICATION = "APPLICATION"
    FRAMEWORK = "FRAMEWORK"
    LIBRARY = "LIBRARY"
    CONTAINER = "CONTAINER"
    DEVICE = "DEVICE"
    FIRMWARE = "FIRMWARE"
    FILE = "FILE"
    OPERATING_SYSTEM = "OPERATING_SYSTEM"
    PLATFORM = "PLATFORM"
    DEVICE_DRIVER = "DEVICE_DRIVER"
    MACHINE_LEARNING_MODEL = "MACHINE_LEARNING_MODEL"
    DATA = "DATA"


class CollectionLogic(Enum):
    """Collection logic for project hierarchy."""

    NONE = "NONE"
    AGGREGATE_LATEST_VERSION_CHILDREN = "AGGREGATE_LATEST_VERSION_CHILDREN"
    AGGREGATE_DIRECT_CHILDREN = "AGGREGATE_DIRECT_CHILDREN"


@dataclass
class ProjectMetadata:
    """Metadata extracted from SBOM files."""

    name: str
    version: str
    description: Optional[str] = None

    @classmethod
    def from_sbom_data(
        cls, sbom_data: Dict[str, Any], fallback_name: str = "unknown"
    ) -> "ProjectMetadata":
        """
        Extract metadata from SBOM JSON data.
        Args:
            sbom_data (Dict[str, Any]): Parsed SBOM JSON data
            fallback_name (str): Fallback name if not found in SBOM
        Returns:
            ProjectMetadata: Extracted metadata
        Raises:
            SBOMFileError: If required metadata is missing
            ValueError: If metadata is invalid
        """
        metadata = sbom_data.get("metadata", {})
        component = metadata.get("component", {})

        name = component.get("name", fallback_name)
        version = component.get("version", "unknown")
        description = component.get("description")

        return cls(name=name, version=version, description=description)


@dataclass
class Project:  # pylint: disable=too-many-instance-attributes
    """
    Represents a Dependency Track project.
    Args:
        name (str): Project name
        version (Optional[str]): Project version
        uuid (Optional[str]): Project UUID
        classifier (ProjectClassifier): Project classifier
        collection_logic (CollectionLogic): Collection logic for project hierarchy
        parent_uuid (Optional[str]): Parent project UUID for hierarchy
        tags (List[str]): List of tags assigned to the project
        description (Optional[str]): Project description
        active (bool): Whether the project is active
        is_latest (bool): Whether the project is marked as latest
    Methods:
        to_api_dict: Convert to dictionary for API calls
    """

    name: str
    version: Optional[str] = None
    uuid: Optional[str] = None
    classifier: ProjectClassifier = ProjectClassifier.APPLICATION
    collection_logic: CollectionLogic = CollectionLogic.NONE
    parent_uuid: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    active: bool = True
    is_latest: bool = False

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        data = {
            "name": self.name,
            "classifier": self.classifier.value,
            "active": self.active,
        }

        if self.version:
            data["version"] = self.version
        if self.description:
            data["description"] = self.description
        if self.parent_uuid:
            data["parent"] = {"uuid": self.parent_uuid}
        if self.tags:
            data["tags"] = [{"name": tag} for tag in self.tags]
        if self.collection_logic != CollectionLogic.NONE:
            data["collectionLogic"] = self.collection_logic.value
        if self.is_latest:
            data["isLatest"] = self.is_latest

        return data


@dataclass
class SBOMFile:
    """
    Represents an SBOM file with its metadata.
    Args:
        path (Path): Path to the SBOM file
        metadata (Optional[ProjectMetadata]): Extracted metadata from the SBOM
    Methods:
        load_metadata: Load and parse metadata from the SBOM file
    Raises:
        FileNotFoundError: If the SBOM file does not exist
        SBOMFileError: If the SBOM file cannot be parsed or is invalid
    """

    path: Path
    metadata: Optional[ProjectMetadata] = None

    def __post_init__(self) -> None:
        """Validate file exists after initialization."""
        # Ensure path is a Path object
        if isinstance(self.path, str):
            self.path = Path(self.path)
        
        if not self.path.exists():
            raise FileNotFoundError(f"SBOM file not found: {self.path}")

    def load_metadata(self) -> ProjectMetadata:
        """Load metadata from the SBOM file."""
        if self.metadata is None:
            try:
                with open(self.path, "r", encoding="utf-8") as file:
                    sbom_data = json.load(file)
                self.metadata = ProjectMetadata.from_sbom_data(
                    sbom_data, self.path.stem
                )
            except (json.JSONDecodeError, SBOMFileError, Exception) as error:
                raise SBOMFileError(
                    f"Failed to parse SBOM file {self.path}: {error}"
                ) from error

        return self.metadata


@dataclass
class UploadResult:
    """Result of an upload operation."""

    success: bool
    project_uuid: Optional[str] = None
    message: str = ""
    token: Optional[str] = None

    @classmethod
    def success_result(
        cls,
        project_uuid: str,
        message: str = "Upload successful",
        token: Optional[str] = None,
    ) -> "UploadResult":
        """
        Create a successful result.
        Args:
            project_uuid (str): UUID of the uploaded project
            message (str): Message describing the result
            token (Optional[str]): Token returned from the upload, if any
        Returns:
            UploadResult: Instance representing a successful upload
        """
        return cls(
            success=True, project_uuid=project_uuid, message=message, token=token
        )

    @classmethod
    def failure_result(cls, message: str) -> "UploadResult":
        """Create a failure result."""
        return cls(success=False, message=message)


@dataclass
class HierarchyConfig:
    """Configuration for hierarchical project structure."""

    version: Optional[str] = None
    collection_logic: CollectionLogic = CollectionLogic.NONE
    classifier: ProjectClassifier = ProjectClassifier.APPLICATION
    tags: List[str] = field(default_factory=list)
    children: List[Dict[str, Any]] = field(default_factory=list)
    sbom_file: Optional[str] = None
    is_latest: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HierarchyConfig":
        """
        Create from dictionary configuration.
        Args:
            data (Dict[str, Any]): Dictionary with configuration
        Returns:
            HierarchyConfig: Instance populated from the dictionary
        Raises:
            ValueError: If configuration values are invalid
        """
        collection_logic = CollectionLogic.NONE
        if "collection_logic" in data:
            try:
                collection_logic = CollectionLogic(data["collection_logic"])
            except ValueError:
                pass  # Use default

        classifier = ProjectClassifier.APPLICATION
        if "classifier" in data:
            try:
                classifier = ProjectClassifier(data["classifier"])
            except ValueError:
                pass  # Use default

        return cls(
            version=data.get("version"),
            collection_logic=collection_logic,
            classifier=classifier,
            tags=data.get("tags", []),
            children=data.get("children", []),
            sbom_file=data.get("sbom_file"),
            is_latest=data.get("is_latest", False),
        )
