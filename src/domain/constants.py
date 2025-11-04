"""Constants used across the SBOM upload application."""

from enum import Enum


class APIConstants:  # pylint: disable=too-few-public-methods
    """API related constants."""

    JSON_CONTENT_TYPE = "application/json"
    AUTO_CREATE_TRUE = "true"
    DEFAULT_TIMEOUT = 300  # Default API timeout in seconds
    DEFAULT_CONNECTION_TEST_TIMEOUT = 30  # Timeout for connection tests


class HTTPStatus(Enum):  # pylint: disable=too-few-public-methods
    """HTTP status codes."""

    OK = 200
    CREATED = 201
    UNAUTHORIZED = 401
    FORBIDDEN = 403
