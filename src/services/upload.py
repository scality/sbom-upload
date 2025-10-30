"""Service for uploading SBOM files to Dependency Track."""

from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Callable
import click
from config.config import AppConfig
from domain.models import SBOMFile
from domain.exceptions import ConfigurationError, UploadError
from services.container import Services


def _determine_sbom_source_path(config: AppConfig) -> Path:
    """
    Determine the SBOM source path based on configuration.

    Args:
        config: Application configuration

    Returns:
        Path: Source path for SBOM files

    Raises:
        ConfigurationError: If no valid SBOM input is configured
    """
    if config.project_sbom_list:
        return Path(config.project_sbom_list)
    if config.project_sbom_dir:
        return Path(config.project_sbom_dir)
    if config.project_sbom:
        return Path(config.project_sbom).parent
    raise ConfigurationError("No SBOM input provided for nested hierarchy")


def _handle_multiple_sbom_upload(
    sbom_files: List[SBOMFile], config: AppConfig, services: Services
) -> None:
    """
    Handle upload of multiple SBOMs.

    Args:
        sbom_files: List of SBOM files to upload
        config: Application configuration
        services: Service container

    Raises:
        UploadError: If all uploads fail
    """
    results = services.sbom_service.upload_multiple_sboms(
        [sbom_file.path for sbom_file in sbom_files], config.project_name, config.project_version
    )

    successful = sum(1 for result in results if result.success)

    if successful == 0:
        raise UploadError("All uploads failed")


def upload_multiple_with_summary(
    sbom_file_retriever: Callable[[], List[SBOMFile]],
    config: AppConfig,
    services: Services,
) -> None:
    """
    Upload multiple SBOMs and display summary with proper error handling.

    This helper function encapsulates the common pattern of:
    1. Retrieving SBOM files
    2. Converting Path objects to SBOMFile objects
    3. Uploading with error handling
    4. Displaying success/failure summary

    Args:
        sbom_file_retriever: Callable that returns list of Paths to SBOM files
        config: Application configuration
        services: Service container

    Raises:
        click.ClickException: If upload fails
    """
    paths = sbom_file_retriever()
    sbom_files = [SBOMFile(path=p) for p in paths]

    try:
        _handle_multiple_sbom_upload(sbom_files, config, services)
        click.echo(f"\nUpload Summary: {len(sbom_files)}/{len(sbom_files)} successful")
    except UploadError as error:
        click.echo(f"\nUpload Summary: 0/{len(sbom_files)} successful")
        raise click.ClickException(str(error))


class SBOMUploader(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for SBOM upload strategies."""

    def __init__(self, config: AppConfig, services: Services) -> None:
        """
        Initialize the uploader with config and services.

        Args:
            config: Application configuration
            services: Service container
        """
        self.config = config
        self.services = services

    @abstractmethod
    def upload(self) -> None:
        """Execute the upload strategy."""
        raise NotImplementedError
