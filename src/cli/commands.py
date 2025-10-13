"""CLI interface for the SBOM upload application."""

from functools import wraps
from typing import Callable, Any
import logging
import click

from config.config import get_config, AppConfig
from domain.exceptions import SBOMUploadError, ConfigurationError
from services.container import Services
from services.upload import SBOMUploader
from sbom_uploader import (
    SingularUploader,
    ListUploader,
    DirectoryUploader,
    NestedUploader,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s][%(name)s][%(funcName)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


def with_services(require_testing: bool = True) -> Callable:
    """
    Decorator that initializes services and optionally tests connection.

    The decorator will:
    1. Check if the function has a 'dry_run' parameter and use it for Services initialization
    2. Add a 'services' parameter to the function call
    3. Optionally test the connection before calling the function

    Args:
        require_testing (bool): Whether to test connection before calling the function

    Usage:
        @with_services()
        def my_command(services: Services) -> None:
            # services is automatically initialized and connection tested
            pass

        @with_services(require_testing=False)
        def my_command(services: Services) -> None:
            # services is initialized but connection is not tested
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current config
            current_config = get_config()

            # Extract dry_run from kwargs or config
            dry_run = kwargs.get("dry_run", current_config.dry_run)

            # Initialize services
            services = Services(dry_run=dry_run)

            # Test connection if requested and not in dry run mode
            if require_testing and not current_config.dry_run:
                services.connection_service.test_connection()

            # Add services to kwargs
            kwargs["services"] = services

            return func(*args, **kwargs)

        return wrapper

    return decorator


@click.group()
@click.version_option(version="1.0.0", package_name="sbom-upload")
def cli() -> None:
    """
    # SBOM GitHub Action CLI

    Command line interface for the SBOM GitHub Action.
    Automatically detects upload mode based on configuration:

    - Single SBOM upload (project_sbom)
    - Multiple SBOM upload from list (project_sbom_list)
    - Multiple SBOM upload from directory (project_sbom_dir)
    - Nested hierarchy upload (parent_name + any SBOM source)

    Configure via environment variables (INPUT_*) for GitHub Action usage.
    """
    click.echo("SBOM GitHub Action CLI")


@cli.command("test-connection")
@with_services(
    require_testing=False
)  # We'll handle connection testing manually for better error messages
def test_connection(services: Services) -> None:
    """
    Test connection to Dependency Track API
    Args:
        None
    Returns:
        None
    Raises:
        SBOMUploadError: If connection test fails
    """
    click.echo(f"Testing connection to {services.connection_service.config.url}...")

    try:
        services.connection_service.test_connection()
    except SBOMUploadError as error:
        click.echo(f"Failed to connect to Dependency Track API: {error}")
        raise click.ClickException("Connection test failed")

    click.echo("Connection to Dependency Track API successful!")


@cli.command("validate-inputs")
def validate_inputs_cmd() -> None:
    """
    Validate all GitHub Action inputs
    Args:
        None
    Returns:
        None
    Raises:
        ConfigurationError: If configuration is invalid
    """
    current_config = get_config()

    try:
        click.echo("Validating GitHub Action inputs...")
        click.echo(f"  - URL: {current_config.url}")
        click.echo(f"  - API Key: {'SET' if current_config.api_key else 'NOT SET'}")
        click.echo(f"  - Project SBOM: {current_config.project_sbom or 'NOT SET'}")
        click.echo(f"  - Project Name: {current_config.project_name or 'NOT SET'}")
        click.echo(
            f"  - Project Version: {current_config.project_version or 'NOT SET'}"
        )
        click.echo(f"  - Project Prefix: {current_config.project_prefix or 'NOT SET'}")
        click.echo(f"  - Project Suffix: {current_config.project_suffix or 'NOT SET'}")
        click.echo(f"  - Parent Name: {current_config.parent_name or 'NOT SET'}")
        click.echo(f"  - Parent Version: {current_config.parent_version or 'NOT SET'}")

        click.echo("\nAll required inputs are valid!")

    except ConfigurationError as error:
        click.echo(f"Configuration error: {error}")
        raise click.ClickException(str(error))


def _get_upload_strategy(config: AppConfig) -> SBOMUploader:
    """
    Factory function to determine the appropriate upload strategy.

    Args:
        config: Application configuration

    Returns:
        SBOMUploader: The appropriate strategy for the given configuration

    Raises:
        click.ClickException: If no valid upload mode is found
    """
    if config.parent_name:
        return NestedUploader()

    if config.project_sbom_list:
        return ListUploader()

    if config.project_sbom_dir:
        return DirectoryUploader()

    if config.project_sbom:
        return SingularUploader()

    raise click.ClickException("No SBOM input provided")


@cli.command("upload")
@with_services()
def upload(services: Services) -> None:
    """
    Main upload command for GitHub Action integration.

    Automatically detects the upload mode based on configuration and delegates
    to the appropriate specialized upload strategy.

    Args:
        services (Services): Service container (injected by decorator)

    Returns:
        None

    Raises:
        SBOMUploadError: If upload fails
    """
    config = get_config()
    config.validate_for_upload()

    click.echo("SBOM Upload Action")
    click.echo("=" * 50)

    try:
        # Get the appropriate upload strategy and execute it
        strategy = _get_upload_strategy(config)
        strategy.upload(config, services)

    except SBOMUploadError as error:
        click.echo(f"{error}")
        raise click.ClickException(str(error))


if __name__ == "__main__":
    cli()
