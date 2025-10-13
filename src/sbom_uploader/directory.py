"""DirectoryUploader implementation for SBOM uploads."""

import click
from config.config import AppConfig
from services.container import Services
from services.upload import SBOMUploader, _handle_multiple_sbom_upload
from services.file_discovery import discover_sbom_files


class DirectoryUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for uploading multiple SBOMs from a directory."""

    def upload(self, config: AppConfig, services: Services) -> None:
        """Upload multiple SBOMs from a directory."""
        click.echo(f"Processing SBOM directory: {config.project_sbom_dir}")

        sbom_files = discover_sbom_files(config.project_sbom_dir)
        _handle_multiple_sbom_upload(sbom_files, config, services)
