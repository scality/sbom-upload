"""File discovery utilities for SBOM files."""

from pathlib import Path
from typing import List, Union
import logging

logger = logging.getLogger(__name__)


def discover_sbom_files(source: Union[str, Path]) -> List[Path]:
    """
    Discover SBOM files from either a directory or a file list.
    Args:
        source: Either a directory path or a file containing a list of SBOM paths
    Returns:
        List[Path]: List of discovered SBOM file paths
    Raises:
        FileNotFoundError: If source doesn't exist
        ValueError: If no SBOM files are found
    """
    source_path = Path(source)

    if not source_path.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    if source_path.is_dir():
        # Directory scanning - find all JSON files
        sbom_files = list(source_path.glob("*.json"))
        logger.info(
            "Found %d JSON files in directory: %s", len(sbom_files), source_path
        )

        if not sbom_files:
            raise ValueError(f"No SBOM files found in: {source}")

        return sbom_files

    if source_path.is_file():
        # File list - read paths from file
        with open(source_path, "r", encoding="utf-8") as file:
            sbom_files = [Path(line.strip()) for line in file if line.strip()]
        logger.info("Read %d SBOM paths from file: %s", len(sbom_files), source_path)

        # Validate that all listed files exist
        missing_files = [file for file in sbom_files if not file.exists()]
        if missing_files:
            raise FileNotFoundError(f"Missing SBOM files: {missing_files}")

        if not sbom_files:
            raise ValueError(f"No SBOM files found in: {source}")

        return sbom_files

    raise ValueError(f"Source must be a directory or file: {source}")
