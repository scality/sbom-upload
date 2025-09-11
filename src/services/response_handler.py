"""Standardized API response handling service."""

from typing import Optional, Union, Dict, Any
import requests
from domain.constants import HTTPStatus
from domain.exceptions import APIConnectionError


class APIResponseHandler:  # pylint: disable=too-few-public-methods
    """Service for standardized API response handling."""

    @staticmethod
    def handle_response(
        response: Optional[requests.Response],
        success_status: int = HTTPStatus.OK,
        operation: str = "API operation",
    ) -> Union[Dict[str, Any], None]:
        """
        Standardized response handling.
        Args:
            response (Optional[requests.Response]): The HTTP response object
            success_status (int): Expected success status code (default: 200)
            operation (str): Description of the operation for error messages
        Returns:
            Union[Dict[str, Any], None]: Parsed JSON response if successful, else None
        Raises:
            APIConnectionError: If the response indicates a failure
        """
        if not response:
            raise APIConnectionError(f"{operation} failed: No response")

        # Handle both integer and enum success status values
        success_value = (
            success_status.value if hasattr(success_status, "value") else success_status
        )

        if response.status_code == success_value:
            return response.json() if response.text else None

        error_msg = f"{operation} failed (status: {response.status_code})"

        if response.text:
            error_msg += f", response: {response.text[:200]}"

        raise APIConnectionError(error_msg)
