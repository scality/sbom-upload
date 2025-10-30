"""Constants used across the SBOM upload application."""

from enum import Enum


class APIConstants:  # pylint: disable=too-few-public-methods
    """API related constants."""

    JSON_CONTENT_TYPE = "application/json"
    AUTO_CREATE_TRUE = "true"


class HTTPStatus(Enum):  # pylint: disable=too-few-public-methods
    """HTTP status codes."""

    OK = 200
    CREATED = 201
    UNAUTHORIZED = 401
    FORBIDDEN = 403
