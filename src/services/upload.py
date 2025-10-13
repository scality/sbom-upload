"""Service for uploading SBOM files to Dependency Track."""

from pathlib import Path
from abc import ABC, abstractmethod
from typing import List
import click
from config.config import AppConfig
from domain.models import SBOMFile
from services.container import Services


def _determine_sbom_source_path(config: AppConfig) -> Path:
    """Determine the SBOM source path based on configuration and log the action."""
    if config.project_sbom_list:
        click.echo(f"Processing SBOM list: {config.project_sbom_list}")
        return Path(config.project_sbom_list).parent
    if config.project_sbom_dir:
        click.echo(f"Processing SBOM directory: {config.project_sbom_dir}")
        return Path(config.project_sbom_dir)
    if config.project_sbom:
        click.echo(f"Processing single SBOM in nested mode: {config.project_sbom}")
        return Path(config.project_sbom).parent
    raise click.ClickException("No SBOM input provided for nested hierarchy")


def _handle_multiple_sbom_upload(
    sbom_files: List[SBOMFile], config: AppConfig, services: Services
) -> None:
    """Handle upload of multiple SBOMs and display summary."""
    results = services.sbom_service.upload_multiple_sboms(
        sbom_files, config.project_name, config.project_version
    )

    successful = sum(1 for result in results if result.success)
    click.echo(f"\nUpload Summary: {successful}/{len(results)} successful")

    if successful == 0:
        raise click.ClickException("All uploads failed")


class SBOMUploader(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for SBOM upload strategies."""

    @abstractmethod
    def upload(self, config: AppConfig, services: Services) -> None:
        """Execute the upload strategy."""
        raise NotImplementedError
