"""Service for uploading SBOM files to Dependency Track."""

from pathlib import Path
from abc import ABC, abstractmethod
import click
from config.config import AppConfig
from domain.models import SBOMFile
from services.container import Services
from services.file_discovery import discover_sbom_files


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


class SBOMUploader(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for SBOM upload strategies."""

    @abstractmethod
    def upload(self, config: AppConfig, services: Services) -> None:
        """Execute the upload strategy."""
        raise NotImplementedError


class NestedHierarchyUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for nested hierarchy uploads."""

    def upload(self, config: AppConfig, services: Services) -> None:
        """Upload SBOMs in nested hierarchy mode."""
        click.echo(f"Using nested hierarchy mode with parent: {config.parent_name}")

        # Determine SBOM source path
        sbom_path = _determine_sbom_source_path(config)

        # Upload nested hierarchy
        parent_name_transformed = config.apply_name_transformations(config.parent_name)
        result = services.sbom_service.upload_nested_hierarchy(
            parent_name_transformed,
            config.parent_version,
            sbom_path,
            config.parent_classifier,
            config.parent_collection_logic,
        )

        if not result.success:
            click.echo(f"{result.message}")
            raise click.ClickException("Nested upload failed")

        click.echo(f"{result.message}")
        click.echo(f"  Parent Project UUID: {result.project_uuid}")


class ListFileUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for uploading multiple SBOMs from a list file."""

    def upload(self, config: AppConfig, services: Services) -> None:
        """Upload multiple SBOMs from a list file."""
        click.echo(f"Processing SBOM list: {config.project_sbom_list}")

        sbom_files = discover_sbom_files(config.project_sbom_list)
        results = services.sbom_service.upload_multiple_sboms(
            sbom_files, config.project_name, config.project_version
        )

        successful = sum(1 for result in results if result.success)
        click.echo(f"\nUpload Summary: {successful}/{len(results)} successful")

        if successful == 0:
            raise click.ClickException("All uploads failed")


class DirectoryUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for uploading multiple SBOMs from a directory."""

    def upload(self, config: AppConfig, services: Services) -> None:
        """Upload multiple SBOMs from a directory."""
        click.echo(f"Processing SBOM directory: {config.project_sbom_dir}")

        sbom_files = discover_sbom_files(config.project_sbom_dir)
        results = services.sbom_service.upload_multiple_sboms(
            sbom_files, config.project_name, config.project_version
        )

        successful = sum(1 for result in results if result.success)
        click.echo(f"\nUpload Summary: {successful}/{len(results)} successful")

        if successful == 0:
            raise click.ClickException("All uploads failed")


class SingleSBOMUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for uploading a single SBOM file."""

    def upload(self, config: AppConfig, services: Services) -> None:
        """Upload a single SBOM file."""
        click.echo(f"Processing single SBOM: {config.project_sbom}")

        sbom_file = SBOMFile(path=Path(config.project_sbom))
        result = services.sbom_service.upload_single_sbom(
            sbom_file, config.project_name, config.project_version
        )

        if not result.success:
            click.echo(f"{result.message}")
            raise click.ClickException("Upload failed")

        click.echo("Upload completed successfully!")
        if result.token:
            click.echo(f"Upload token: {result.token}")
