"""Custom exceptions for the SBOM upload application."""


class SBOMUploadError(Exception):
    """Base exception for SBOM upload operations."""


class ConfigurationError(SBOMUploadError):
    """Raised when there are configuration validation errors."""


class APIConnectionError(SBOMUploadError):
    """Raised when unable to connect to Dependency Track API."""


class AuthenticationError(SBOMUploadError):
    """Raised when API authentication fails."""


class ProjectCreationError(SBOMUploadError):
    """Raised when project creation fails."""


class SBOMFileError(SBOMUploadError):
    """Raised when there are issues with SBOM files."""


class UploadError(SBOMUploadError):
    """Raised when upload operations fail."""


class ValidationError(SBOMUploadError):
    """Raised when input validation fails."""
