"""NestedHierarchyUploader implementation for SBOM uploads."""

import click
from config.config import AppConfig
from services.container import Services
from services.upload import SBOMUploader, _determine_sbom_source_path


class NestedUploader(SBOMUploader):  # pylint: disable=too-few-public-methods
    """Strategy for nested hierarchy uploads."""

    def upload(self, config: AppConfig, services: Services) -> None:
        """Upload SBOMs in nested hierarchy mode."""
        click.echo(f"Using nested hierarchy mode with parent: {config.parent_name}")

        # Determine SBOM source path
        sbom_path = _determine_sbom_source_path(config)

        # Upload nested hierarchy
        # Note: Parent project name should not have prefix/suffix transformations applied
        # Only child projects should use the project_prefix/project_suffix
        result = services.sbom_service.upload_nested_hierarchy(
            config.parent_name,
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
