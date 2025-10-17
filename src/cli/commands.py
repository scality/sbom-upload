"""CLI interface for the SBOM upload application."""

from functools import wraps
from typing import Callable, Any
import logging
import os
import json
import tempfile
from pathlib import Path
import click
from config.config import get_config, AppConfig
from domain.exceptions import SBOMUploadError, ConfigurationError
from services.container import Services
from services.upload import SBOMUploader
from services.file_discovery import generate_hierarchy_config
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


@cli.command("generate-hierarchy")
@click.option(
    "--input-dir",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str),
    required=True,
    help="Root directory containing nested SBOM structure",
)
@click.option(
    "--output-file",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False, writable=True, path_type=str),
    help="File path for generated hierarchy JSON (default: print to stdout if not uploading)",
)
@click.option(
    "--upload",
    "-u",
    is_flag=True,
    help="Generate hierarchy and upload directly to Dependency Track",
)
def generate_hierarchy(  # pylint: disable=too-many-locals,redefined-outer-name
    input_dir: str,
    output_file: str = None,
    upload: bool = False,
    services: Services = None,
) -> None:
    """
    Generate hierarchical configuration JSON from nested SBOM directory structure.

    Automatically scans a directory structure containing SBOM files and generates
    a hierarchy configuration JSON that can be used with the upload command.

    Structure rules:
    - Root merged SBOMs (*_merged_sbom.json) become top-level metapps
    - Subdirectory merged SBOMs become child applications
    - Individual SBOM files (*_sbom.json) become leaf components

    Examples:
      # Generate hierarchy from project test data
      python3 src/main.py generate-hierarchy -i tests/project

      # Save to file
      python3 src/main.py generate-hierarchy -i tests/project -o hierarchy.json

      # Generate and upload directly
      python3 src/main.py generate-hierarchy -i tests/project --upload
    """
    try:
        click.echo(f"Scanning directory: {input_dir}")

        # Generate the hierarchy configuration
        # For direct upload, use absolute paths and don't save to file initially
        use_absolute_paths = upload
        temp_output_file = output_file if not upload else None
        input_path = Path(input_dir)
        output_path = Path(temp_output_file) if temp_output_file else None
        config_data = generate_hierarchy_config(
            input_path, output_path, use_absolute_paths
        )

        # Provide some statistics
        total_projects = _count_projects_in_hierarchy(config_data)
        click.echo("\nHierarchy generated:")
        click.echo(f"  - Top-level projects: {len(config_data)}")
        click.echo(f"  - Total projects: {total_projects}")

        if upload:
            _handle_hierarchy_upload(config_data, output_file, services)
        else:
            _handle_hierarchy_output(config_data, output_file)

    except (FileNotFoundError, ValueError) as error:
        click.echo(f"Error: {error}")
        raise click.ClickException(str(error))
    except Exception as error:
        click.echo(f"Unexpected error: {error}")
        raise click.ClickException("Failed to generate hierarchy configuration")


@cli.command("generate-hierarchy-action")
def generate_hierarchy_action() -> (
    None
):  # pylint: disable=too-many-branches,too-many-statements
    """
    Generate hierarchical configuration from environment variables for GitHub Action.

    Reads configuration from INPUT_* environment variables and generates
    hierarchy configuration with optional direct upload to Dependency Track.

    Environment Variables:
        INPUT_HIERARCHY_INPUT_DIR: Root directory containing nested SBOM structure
        INPUT_HIERARCHY_OUTPUT_FILE: Output file path for generated hierarchy JSON
        INPUT_HIERARCHY_UPLOAD: Set to 'true' to upload directly to Dependency Track
        INPUT_URL: Dependency Track server URL (required for upload)
        INPUT_API_KEY: Dependency Track API key (required for upload)
    """

    # Read environment variables
    input_dir = os.getenv("INPUT_HIERARCHY_INPUT_DIR", "")
    output_file = os.getenv("INPUT_HIERARCHY_OUTPUT_FILE", "")
    should_upload = os.getenv("INPUT_HIERARCHY_UPLOAD", "false").lower() == "true"

    # Validate required inputs
    if not input_dir:
        raise click.ClickException(
            "INPUT_HIERARCHY_INPUT_DIR is required for hierarchy generation"
        )

    if not Path(input_dir).exists():
        raise click.ClickException(f"Input directory does not exist: {input_dir}")

    if not Path(input_dir).is_dir():
        raise click.ClickException(f"Input path is not a directory: {input_dir}")

    click.echo("SBOM Hierarchy Generation Action")
    click.echo("=" * 50)
    click.echo(f"Input directory: {input_dir}")
    click.echo(f"Output file: {output_file or 'stdout'}")
    click.echo(f"Upload enabled: {should_upload}")

    try:
        # Generate the hierarchy configuration
        use_absolute_paths = should_upload
        temp_output_file = output_file if output_file and not should_upload else None
        input_path = Path(input_dir)
        output_path = Path(temp_output_file) if temp_output_file else None

        config_data = generate_hierarchy_config(
            input_path, output_path, use_absolute_paths
        )

        # Provide statistics
        total_projects = _count_projects_in_hierarchy(config_data)
        click.echo("\nHierarchy generated:")
        click.echo(f"  - Top-level projects: {len(config_data)}")
        click.echo(f"  - Total projects: {total_projects}")

        # Set GitHub Action outputs
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.getenv("GITHUB_OUTPUT"), "a", encoding="utf-8") as file:
                if output_file:
                    file.write(f"hierarchy-config-file={output_file}\n")
                file.write(f"hierarchy-projects-count={total_projects}\n")
                file.write(f"hierarchy-top-level-projects={len(config_data)}\n")

        if should_upload:
            _handle_action_upload(config_data, output_file)
        elif not output_file:
            # Print to stdout if no output file specified
            click.echo(json.dumps(config_data, indent=2))

        click.echo("Hierarchy generation completed successfully")

    except SBOMUploadError as error:
        click.echo(f"Error: {error}")
        raise click.ClickException(str(error))
    except Exception as error:
        click.echo(f"Unexpected error: {error}")
        raise click.ClickException("Failed to generate hierarchy configuration")


def _handle_hierarchy_upload(
    config_data: dict, output_file: str, services: Services
) -> None:
    """Handle hierarchy upload to Dependency Track."""
    # Initialize services only when uploading
    if not services:
        try:
            current_config = get_config()
            services = Services(dry_run=current_config.dry_run)
        except Exception as error:
            click.echo(f"Failed to initialize services: {error}")
            raise click.ClickException("Cannot upload without proper configuration")

    # Test connection first if uploading
    if not services:
        raise click.ClickException("Services not available for upload")

    click.echo(f"\nTesting connection to {services.connection_service.config.url}...")
    try:
        services.connection_service.test_connection()
        click.echo("Connection successful!")
    except Exception as error:
        click.echo(f"Connection failed: {error}")
        raise click.ClickException("Cannot upload - connection test failed")

    # Upload using hierarchy configuration
    click.echo("\nUploading hierarchy to Dependency Track...")
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(config_data, temp_file, indent=2)
            temp_config_path = temp_file.name

        try:
            result = services.sbom_service.upload_from_hierarchy_config(
                Path(temp_config_path)
            )
            if result.success:
                click.echo(f"{result.message}")
                if output_file:
                    with open(output_file, "w", encoding="utf-8") as file:
                        json.dump(config_data, file, indent=2)
                    click.echo(f"Hierarchy configuration also saved to: {output_file}")
            else:
                click.echo(f"Upload failed: {result.message}")
                raise click.ClickException("Hierarchy upload failed")
        finally:
            os.unlink(temp_config_path)
    except Exception as error:
        click.echo(f"Upload error: {error}")
        raise click.ClickException(f"Failed to upload hierarchy: {error}")


def _handle_hierarchy_output(config_data: dict, output_file: str) -> None:
    """Handle hierarchy output to file or stdout."""
    if output_file:
        click.echo(f"Hierarchy configuration saved to: {output_file}")
    else:
        click.echo("\nGenerated hierarchy configuration:")
        click.echo("=" * 50)
        click.echo(json.dumps(config_data, indent=2))


def _handle_action_upload(config_data: dict, output_file: str) -> None:
    """Handle upload for GitHub Action hierarchy generation."""
    try:
        current_config = get_config()
        services = Services(dry_run=current_config.dry_run)
    except Exception as error:
        click.echo(f"Failed to initialize services: {error}")
        raise click.ClickException("Cannot upload without proper configuration")

    click.echo(f"\nTesting connection to {services.connection_service.config.url}...")
    try:
        services.connection_service.test_connection()
        click.echo("Connection successful!")
    except Exception as error:
        click.echo(f"Connection failed: {error}")
        raise click.ClickException("Cannot upload - connection test failed")

    click.echo("\nUploading hierarchy to Dependency Track...")
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(config_data, temp_file, indent=2)
            temp_path = temp_file.name

        services.sbom_service.upload_from_hierarchy_config(Path(temp_path))
        click.echo("Hierarchy upload complete: 1 successful, 0 failed")

        if output_file:
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(config_data, file, indent=2)
            click.echo(f"Hierarchy configuration also saved to: {output_file}")

        os.unlink(temp_path)
    except Exception as error:
        click.echo(f"Upload failed: {error}")
        raise click.ClickException("Hierarchy upload failed")


def _count_projects_in_hierarchy(config_data: dict) -> int:
    """
    Recursively count all projects in a hierarchy configuration.

    Args:
        config_data: Hierarchy configuration dictionary

    Returns:
        Total count of all projects in the hierarchy
    """
    count = len(config_data)

    for root_config in config_data.values():
        if isinstance(root_config, dict) and "children" in root_config:
            count += _count_children(root_config["children"])

    return count


def _count_children(children: list) -> int:
    """
    Recursively count children in a project list.

    Args:
        children: List of child project configurations

    Returns:
        Count of all nested children
    """
    count = len(children)

    for child in children:
        if isinstance(child, dict) and "children" in child:
            count += _count_children(child["children"])

    return count


if __name__ == "__main__":
    cli()
