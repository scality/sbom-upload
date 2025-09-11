"""Connection service for Dependency Track API."""

import logging
from typing import Optional
import requests

from config.config import AppConfig
from domain.exceptions import APIConnectionError, AuthenticationError
from domain.constants import APIConstants, HTTPStatus
from services.response_handler import APIResponseHandler

logger = logging.getLogger(__name__)


class ConnectionService:
    """Service for managing API connections."""

    def __init__(self, config: AppConfig, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self.headers = {
            "X-API-Key": config.api_key,
            "Content-Type": APIConstants.JSON_CONTENT_TYPE,
        }

    def test_connection(self) -> bool:
        """
        Test the API connection and authentication.
        Args:
            None
        Returns:
            bool: True if connection is successful, False otherwise
        Raises:
            APIConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        if self.dry_run:
            logger.info("[DRY RUN] Skipping connection test")
            return

        logger.info("Testing API connection...")
        url = f"{self.config.url}/project"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            # Handle authentication errors separately since they need specific exceptions
            if response.status_code == 401:
                raise AuthenticationError("API authentication failed - invalid API key")
            if response.status_code == 403:
                raise AuthenticationError(
                    "API access forbidden - insufficient permissions"
                )

            # Use response handler for standard success/error handling
            APIResponseHandler.handle_response(
                response, success_status=200, operation="Connection test"
            )
            logger.info("API connection successful")
            return

        except (  # pylint: disable=try-except-raise
            AuthenticationError,
            APIConnectionError,
        ):
            raise
        except requests.exceptions.ConnectionError as exc:
            raise APIConnectionError(f"Unable to connect to {self.config.url}") from exc
        except requests.exceptions.Timeout as exc:
            raise APIConnectionError("Connection timeout") from exc
        except requests.exceptions.RequestException as error:
            raise APIConnectionError(f"Request failed: {str(error)}") from error

    def make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[requests.Response]:
        """
        Make an authenticated API request.
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint (relative to base URL)
            **kwargs: Additional arguments for requests.request()
        Returns:
            Optional[requests.Response]: Response object or None for dry run
        Raises:
            APIConnectionError: If the request fails
            AuthenticationError: If authentication fails
        """
        if self.dry_run and method.upper() in ["POST", "PUT", "DELETE"]:
            logger.info("[DRY RUN] Would %s to %s", method.upper(), endpoint)
            return None

        url = f"{self.config.url}/{endpoint.lstrip('/')}"

        # Prepare headers - remove Content-Type for file uploads
        headers = self.headers.copy()
        if "files" in kwargs:
            # For file uploads, let requests set the Content-Type automatically
            headers.pop("Content-Type", None)

        try:
            response = requests.request(
                method=method, url=url, headers=headers, timeout=30, **kwargs
            )

            # Handle authentication errors separately since they need specific exceptions
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                raise AuthenticationError("API authentication failed")
            if response.status_code == HTTPStatus.FORBIDDEN:
                raise AuthenticationError("API access forbidden")

            return response

        except (  # pylint: disable=try-except-raise
            AuthenticationError,
            APIConnectionError,
        ):
            raise
        except requests.exceptions.RequestException as error:
            raise APIConnectionError(f"API request failed: {str(error)}") from error
