"""Configuration management for the SBOM upload application."""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin
from pathlib import Path
from domain.exceptions import ConfigurationError, ValidationError


@dataclass
class AppConfig:  # pylint: disable=too-many-instance-attributes
    """
    Application configuration with validation.
    Args:
        url (str): Base URL of the Dependency Track instance
        api_key (str): API key for authentication
        project_sbom (Optional[str]): Path to a single SBOM file to upload
        project_sbom_list (Optional[str]): Path to a file containing list of SBOM files
        project_sbom_dir (Optional[str]): Path to a directory containing SBOM files
        project_name (Optional[str]): Project name override
        project_version (Optional[str]): Project version override
        project_description (Optional[str]): Project description override
        project_uuid (Optional[str]): Project UUID override
        project_prefix (Optional[str]): Prefix to add to project name
        project_suffix (Optional[str]): Suffix to add to project name
        project_classifier (str): Project classifier (default: "APPLICATION")
        project_collection_logic (str): Collection logic for project hierarchy (default: "NONE")
        is_latest (bool): Whether to mark the project as latest (default: False)
        auto_detect_latest (bool): Auto-detect if the project is the latest version (default: True)
        project_tags (Optional[str]): Comma-separated list of tags to assign to the project
        parent_name (Optional[str]): Parent project name for nested hierarchy
        parent_version (Optional[str]): Parent project version for nested hierarchy
        parent_classifier (str): Parent project classifier (default: "APPLICATION")
        parent_collection_logic (str): Parent project collection logic
            (default: "AGGREGATE_LATEST_VERSION_CHILDREN")
        dry_run (bool): If True, perform a dry run without making changes (default: False)
    Raises:
        ConfigurationError: If required configuration is missing or invalid
        ValidationError: If validation of specific fields fails
    Methods:
        from_environment: Create configuration from environment variables
        validate_for_upload: Additional validation specifically for upload operations
    """

    # Required fields
    url: str
    api_key: str

    # Optional project fields
    project_sbom: Optional[str] = None
    project_sbom_list: Optional[str] = None
    project_sbom_dir: Optional[str] = None
    project_name: Optional[str] = None
    project_version: Optional[str] = None
    project_description: Optional[str] = None
    project_uuid: Optional[str] = None
    project_prefix: Optional[str] = None
    project_suffix: Optional[str] = None
    project_classifier: str = "APPLICATION"
    project_collection_logic: str = "NONE"

    # Parent project fields for nested hierarchy
    parent_name: Optional[str] = None
    parent_version: Optional[str] = None
    parent_classifier: str = "APPLICATION"
    parent_collection_logic: str = "AGGREGATE_LATEST_VERSION_CHILDREN"

    # Feature flags
    is_latest: bool = False
    auto_detect_latest: bool = True
    dry_run: bool = False

    # Tags
    project_tags: Optional[str] = None

    # Hierarchy inputs
    hierarchy_input_dir: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()
        self._normalize()

    def _validate(self) -> None:
        """
        Validate required configuration.
        Args:
            None
        Returns:
            None
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Skip validation in dry run mode
        if self.dry_run:
            return

        errors = []

        if not self.url:
            errors.append("URL is required")

        if not self.api_key:
            errors.append("API key is required")

        # Note: project_sbom validation is done separately in validate_for_upload()
        # since not all operations require SBOM files (e.g., test-connection)

        if errors:
            raise ConfigurationError(
                f"Configuration validation failed: {', '.join(errors)}"
            )

    def _normalize(self) -> None:
        """
        Normalize configuration values.
        Args:
            None
        Returns:
            None
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Ensure URL has proper API path
        self.url = self.url.rstrip("/")
        if not self.url.endswith("/api/v1"):
            self.url = urljoin(self.url + "/", "api/v1")

    def apply_name_transformations(self, name: str) -> str:
        """
        Apply prefix and suffix transformations to a project name.

        Args:
            name (str): The base project name

        Returns:
            str: The transformed project name with prefix/suffix applied
        """
        if not name:
            return name

        result = name

        if self.project_prefix:
            result = f"{self.project_prefix}{result}"

        if self.project_suffix:
            result = f"{result}{self.project_suffix}"

        return result

    @classmethod
    def from_environment(cls) -> "AppConfig":
        """
        Create configuration from environment variables.
        Args:
            None
        Returns:
            AppConfig: Instance populated from environment variables
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        return cls(
            url=os.getenv("INPUT_URL", "").strip(),
            api_key=os.getenv("INPUT_API_KEY", "").strip(),
            project_sbom=os.getenv("INPUT_PROJECT_SBOM", "").strip() or None,
            project_sbom_list=os.getenv("INPUT_PROJECT_SBOM_LIST", "").strip() or None,
            project_sbom_dir=os.getenv("INPUT_PROJECT_SBOM_DIR", "").strip() or None,
            project_name=os.getenv("INPUT_PROJECT_NAME", "").strip() or None,
            project_version=os.getenv("INPUT_PROJECT_VERSION", "").strip() or None,
            project_description=os.getenv("INPUT_PROJECT_DESCRIPTION", "").strip()
            or None,
            project_uuid=os.getenv("INPUT_PROJECT_UUID", "").strip() or None,
            project_prefix=os.getenv("INPUT_PROJECT_PREFIX", "").strip() or None,
            project_suffix=os.getenv("INPUT_PROJECT_SUFFIX", "").strip() or None,
            project_classifier=os.getenv(
                "INPUT_PROJECT_CLASSIFIER", "APPLICATION"
            ).strip(),
            project_collection_logic=os.getenv(
                "INPUT_PROJECT_COLLECTION_LOGIC", "NONE"
            ).strip(),
            project_tags=os.getenv("INPUT_PROJECT_TAGS", "").strip() or None,
            is_latest=os.getenv("INPUT_IS_LATEST", "false").strip().lower() == "true",
            auto_detect_latest=os.getenv("INPUT_AUTO_DETECT_LATEST", "true")
            .strip()
            .lower()
            == "true",
            dry_run=os.getenv("INPUT_DRY_RUN", "false").strip().lower() == "true",
            parent_name=os.getenv("INPUT_PARENT_PROJECT_NAME", "").strip() or None,
            parent_version=os.getenv("INPUT_PARENT_PROJECT_VERSION", "").strip()
            or None,
            parent_classifier=os.getenv(
                "INPUT_PARENT_PROJECT_CLASSIFIER", "APPLICATION"
            ).strip(),
            parent_collection_logic=os.getenv(
                "INPUT_PARENT_PROJECT_COLLECTION_LOGIC",
                "AGGREGATE_LATEST_VERSION_CHILDREN",
            ).strip(),
            hierarchy_input_dir=os.getenv("INPUT_HIERARCHY_INPUT_DIR", "").strip() or None,
        )

    def validate_for_upload(self) -> None:
        """
        Additional validation specifically for upload operations.
        Args:
            None
        Returns:
            None
        Raises:
            ValidationError: If validation of specific fields fails
        """
        # Check that at least one SBOM input is provided
        if (
            not self.project_sbom
            and not self.project_sbom_list
            and not self.project_sbom_dir
            and not self.hierarchy_input_dir
        ):
            raise ValidationError(
                "Either project_sbom, project_sbom_list, project_sbom_dir, "
                "or hierarchy_input_dir is required for upload operations"
            )

        if self.project_sbom:
            if not Path(self.project_sbom).exists():
                raise ValidationError(f"SBOM file not found: {self.project_sbom}")

        if self.project_sbom_list:
            if not Path(self.project_sbom_list).exists():
                raise ValidationError(
                    f"SBOM list file not found: {self.project_sbom_list}"
                )

        if self.project_sbom_dir:
            if not Path(self.project_sbom_dir).exists():
                raise ValidationError(
                    f"SBOM directory not found: {self.project_sbom_dir}"
                )
            if not Path(self.project_sbom_dir).is_dir():
                raise ValidationError(
                    f"SBOM directory path is not a directory: {self.project_sbom_dir}"
                )

        if self.hierarchy_input_dir:
            if not Path(self.hierarchy_input_dir).exists():
                raise ValidationError(
                    f"Hierarchy input directory not found: {self.hierarchy_input_dir}"
                )
            if not Path(self.hierarchy_input_dir).is_dir():
                raise ValidationError(
                    f"Hierarchy input directory path is not a directory: {self.hierarchy_input_dir}"
                )


def get_config() -> AppConfig:
    """
    Get application configuration from environment.
    Args:
        None
    Returns:
        AppConfig: Instance populated from environment variables
    Raises:
        ConfigurationError: If required configuration is missing or invalid
        ValidationError: If validation of specific fields fails
    """
    return AppConfig.from_environment()
