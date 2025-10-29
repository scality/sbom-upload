"""NestedHierarchyUploader implementation for SBOM uploads."""

import click
from domain.exceptions import ConfigurationError, UploadError
from services.upload import SBOMUploader, _determine_sbom_source_path


class NestedUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for nested hierarchy uploads."""

    def upload(self) -> None:
        """Upload SBOMs in nested hierarchy mode."""
        click.echo(
            f"Using nested hierarchy mode with parent: {self.config.parent_name}"
        )

        try:
            # Determine SBOM source path
            sbom_path = _determine_sbom_source_path(self.config)

            # Log the source being processed
            if self.config.project_sbom_list:
                click.echo(f"Processing SBOM list: {self.config.project_sbom_list}")
            elif self.config.project_sbom_dir:
                click.echo(f"Processing SBOM directory: {self.config.project_sbom_dir}")
            elif self.config.project_sbom:
                click.echo(f"Processing single SBOM: {self.config.project_sbom}")

            # Upload nested hierarchy
            # Note: Parent project name should not have prefix/suffix transformations applied
            # Only child projects should use the project_prefix/project_suffix
            result = self.services.sbom_service.upload_nested_hierarchy(
                self.config.parent_name,
                self.config.parent_version,
                sbom_path,
                self.config.parent_classifier,
                self.config.parent_collection_logic,
            )

            if not result.success:
                click.echo(f"{result.message}")
                raise click.ClickException("Nested upload failed")

            click.echo(f"{result.message}")
            click.echo(f"  Parent Project UUID: {result.project_uuid}")

        except ConfigurationError as error:
            raise click.ClickException(str(error))
        except UploadError as error:
            raise click.ClickException(str(error))
