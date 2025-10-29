"""SingleUploader implementation for SBOM uploads."""

from pathlib import Path
import click
from domain.models import SBOMFile
from services.upload import SBOMUploader


class SingularUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for uploading a single SBOM file."""

    def upload(self) -> None:
        """Upload a single SBOM file."""
        click.echo(f"Processing single SBOM: {self.config.project_sbom}")

        sbom_file = SBOMFile(path=Path(self.config.project_sbom))
        result = self.services.sbom_service.upload_single_sbom(
            sbom_file, self.config.project_name, self.config.project_version
        )

        if not result.success:
            click.echo(f"{result.message}")
            raise click.ClickException("Upload failed")

        click.echo("Upload completed successfully!")
        if result.token:
            click.echo(f"Upload token: {result.token}")
