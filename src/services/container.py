"""Service container for dependency injection."""

from config.config import get_config
from services.connection import ConnectionService
from services.project import ProjectService
from services.sbom import SBOMService


class Services:  # pylint: disable=too-few-public-methods
    """Container for service instances."""

    def __init__(self, dry_run: bool = False) -> None:
        self.config = get_config()
        self.connection_service = ConnectionService(self.config, dry_run=dry_run)
        self.project_service = ProjectService(self.connection_service)
        self.sbom_service = SBOMService(self.connection_service, self.project_service)
