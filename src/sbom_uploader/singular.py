"""SingleUploader implementation for SBOM uploads."""

from pathlib import Path
import click
from config.config import AppConfig
from domain.models import SBOMFile
from services.container import Services
from services.upload import SBOMUploader


class SingularUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
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
