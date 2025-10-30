"""File discovery utilities for SBOM files."""

from pathlib import Path
from typing import List, Union, Dict, Any, Optional
import logging
import re
import json
import hashlib

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


def _parse_sbom_filename(filename: str) -> Optional[Dict[str, Any]]:
    """
    Parse SBOM filename to extract component name, version, and type.

    Expected patterns:
    - name_version_merged_sbom.json (merged SBOM - has children)
    - name_version_sbom.json (leaf component)

    Args:
        filename: SBOM filename to parse

    Returns:
        Dict with 'name', 'version', 'is_merged' keys, or None if parsing fails
    """
    # Remove .json extension
    base_name = filename.replace(".json", "")

    # Check for merged SBOM pattern
    merged_pattern = r"^(.+)_(.+?)_merged_sbom$"
    merged_match = re.match(merged_pattern, base_name)

    if merged_match:
        return {
            "name": merged_match.group(1),
            "version": merged_match.group(2),
            "is_merged": True,
        }

    # Check for regular SBOM pattern
    sbom_pattern = r"^(.+)_(.+?)_sbom$"
    sbom_match = re.match(sbom_pattern, base_name)

    if sbom_match:
        return {
            "name": sbom_match.group(1),
            "version": sbom_match.group(2),
            "is_merged": False,
        }

    # Try to handle edge cases where version might contain underscores
    # Split by underscores and try different combinations
    parts = base_name.split("_")
    if len(parts) >= 3:
        # Try different positions for version splitting
        for i in range(1, len(parts) - 1):
            if parts[-1] == "sbom" or (
                len(parts) >= 2 and parts[-2:] == ["merged", "sbom"]
            ):
                is_merged = parts[-2:] == ["merged", "sbom"]
                end_offset = 2 if is_merged else 1

                name = "_".join(parts[:i])
                version = "_".join(parts[i:-end_offset])

                if name and version:
                    return {"name": name, "version": version, "is_merged": is_merged}

    logger.warning("Could not parse SBOM filename: %s", filename)
    return None


def generate_hierarchy_config(
    root_path: Path,
    output_path: Optional[Path] = None,
    use_absolute_paths: bool = False,
) -> Dict[str, Any]:
    """
    Generate a hierarchical configuration from an SBOM directory structure.

    Args:
        root_path: Path to the directory containing SBOM files
        output_path: Optional path to save the configuration JSON
        use_absolute_paths: If True, use absolute paths for SBOM files (needed for direct upload)

    Returns:
        Dictionary containing the hierarchical configuration
    """
    if not root_path.exists():
        raise FileNotFoundError(f"Root directory not found: {root_path}")

    if not root_path.is_dir():
        raise ValueError(f"Path must be a directory: {root_path}")

    logger.info("Generating hierarchy config from: %s", root_path)

    hierarchy_config = {}

    # Find top-level merged SBOMs in root directory
    root_merged_sboms = list(root_path.glob("*_merged_sbom.json"))

    if not root_merged_sboms:
        # If no root merged SBOMs, create a single metapp from directory name
        metapp_name = root_path.name
        logger.info("No root merged SBOMs found, creating metapp: %s", metapp_name)

        hierarchy_config[f"meta_{metapp_name}"] = {
            "version": None,
            "collection_logic": "AGGREGATE_LATEST_VERSION_CHILDREN",
            "classifier": "APPLICATION",
            "tags": [metapp_name.lower(), "meta"],
            "children": [],
        }

        # Process subdirectories as children, or if no subdirectories, process root files
        children = _process_directory_children(root_path)

        # If no subdirectories found, check for individual SBOM files in root
        if not children:
            root_leaf_components = _find_leaf_components(
                root_path,
                root_path,
                use_absolute_paths,
                parent_name=f"meta_{metapp_name}",
            )
            children = root_leaf_components

        hierarchy_config[f"meta_{metapp_name}"]["children"] = children

    else:
        # Process each root merged SBOM as a top-level metapp
        for merged_sbom in root_merged_sboms:
            parsed = _parse_sbom_filename(merged_sbom.name)
            if not parsed:
                continue

            metapp_name = parsed["name"]
            metapp_version = parsed["version"]

            logger.info("Processing metapp: %s v%s", metapp_name, metapp_version)

            # Create 3-level hierarchy:
            # Level 1: meta_{name} (collection)
            # Level 2: {name}_{version} (collection)
            # Level 3: All individual SBOM components (leaf)

            # Process subdirectories as children first
            children = _process_directory_children(root_path, use_absolute_paths)

            # Also check for individual SBOMs in the same directory as the merged SBOM
            # (for flat structures where all components are in the same directory)
            individual_components = _find_leaf_components(
                root_path,
                root_path,
                use_absolute_paths,
                parent_name=f"{metapp_name}_{metapp_version}",
            )
            children.extend(individual_components)

            # Create Level 2: {name}_{version} with all components as children
            level2_project = {
                "name": f"{metapp_name}_{metapp_version}",
                "version": metapp_version,
                "collection_logic": "AGGREGATE_DIRECT_CHILDREN",
                "classifier": "APPLICATION",
                "tags": [
                    metapp_name.lower().replace("-", "_"),
                    f"{metapp_name}_{metapp_version}",
                ],
                "children": children,
            }

            # Create Level 1: meta_{name} with Level 2 as its only child
            hierarchy_config[f"meta_{metapp_name}"] = {
                "version": None,
                "collection_logic": "AGGREGATE_LATEST_VERSION_CHILDREN",
                "classifier": "APPLICATION",
                "tags": [metapp_name.lower().replace("-", "_"), "meta"],
                "children": [level2_project],
            }

    if not hierarchy_config:
        raise ValueError(f"No valid SBOM structure found in: {root_path}")

    # Save to file if specified
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(hierarchy_config, f, indent=2)
        logger.info("Hierarchy config saved to: %s", output_path)

    return hierarchy_config


def _process_directory_children(
    directory: Path, use_absolute_paths: bool = False
) -> List[Dict[str, Any]]:
    """
    Process subdirectories to find child applications and leaf components.

    Args:
        directory: Directory to scan for children

    Returns:
        List of child project configurations
    """
    children = []

    # Process each subdirectory
    for subdir in directory.iterdir():
        if not subdir.is_dir():
            continue

        logger.debug("Processing subdirectory: %s", subdir.name)

        # Look for merged SBOM in subdirectory (child application)
        merged_sboms = list(subdir.glob("*_merged_sbom.json"))

        if merged_sboms:
            # This subdirectory contains a child application
            for merged_sbom in merged_sboms:
                parsed = _parse_sbom_filename(merged_sbom.name)
                if not parsed:
                    continue

                # Find leaf components in this subdirectory
                leaf_components = _find_leaf_components(
                    subdir,
                    None,
                    use_absolute_paths,
                    parent_name=f"meta_{parsed['name']}",
                )

                # Create collection project for this sub-application (merged SBOM is NOT uploaded)
                child_app = {
                    "name": f"meta_{parsed['name']}",
                    "version": parsed["version"],
                    "collection_logic": "AGGREGATE_DIRECT_CHILDREN",
                    "classifier": "APPLICATION",
                    "tags": [parsed["name"].lower().replace("-", "_"), "meta"],
                    "children": leaf_components,
                }
                children.append(child_app)

        else:
            # No merged SBOM, check if there are individual SBOMs to create a virtual group
            leaf_components = _find_leaf_components(
                subdir, None, use_absolute_paths, parent_name=f"meta_{subdir.name}"
            )
            if leaf_components:
                # Create a virtual application group for this subdirectory
                child_app = {
                    "name": f"meta_{subdir.name}",
                    "version": None,
                    "collection_logic": "AGGREGATE_DIRECT_CHILDREN",
                    "classifier": "APPLICATION",
                    "tags": [subdir.name.lower().replace("-", "_"), "meta"],
                    "children": leaf_components,
                }
                children.append(child_app)

    return children


def _find_leaf_components(
    directory: Path,
    root_dir: Optional[Path] = None,
    use_absolute_paths: bool = False,
    parent_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find individual SBOM files (leaf components) in a directory.

    Args:
        directory: Directory to scan for leaf SBOMs
        root_dir: Root directory for calculating relative paths (optional)
        use_absolute_paths: If True, use absolute paths for SBOM files
        parent_name: Name of the parent project to use as suffix for uniqueness

    Returns:
        List of leaf component configurations
    """
    leaf_components = []

    # Find all non-merged SBOM files
    sbom_files = list(directory.glob("*_sbom.json"))
    # Exclude merged SBOMs
    sbom_files = [f for f in sbom_files if "_merged_sbom.json" not in f.name]

    for sbom_file in sbom_files:
        parsed = _parse_sbom_filename(sbom_file.name)
        if not parsed or parsed["is_merged"]:
            continue

        # Calculate path based on use_absolute_paths flag
        if use_absolute_paths:
            sbom_path = str(sbom_file.resolve())
        else:
            # Calculate relative path based on context
            if root_dir:
                # If we have root_dir, calculate relative to its parent
                sbom_path = str(sbom_file.relative_to(root_dir.parent))
            else:
                # Default behavior for nested structure
                sbom_path = str(sbom_file.relative_to(directory.parent.parent))

        # Generate a deterministic suffix based on parent project name to avoid duplicates
        # This ensures the same project name is used across multiple GitHub Action runs
        # and creates a relationship between parent and child projects
        identifier = (
            parent_name.lower().replace(" ", "-").replace("_", "-")
            if parent_name
            else hashlib.sha256(sbom_path.encode()).hexdigest()[:8]
        )
        unique_name = f"{parsed['name']}-{identifier}"

        component = {
            "name": unique_name,
            "version": parsed["version"],
            "collection_logic": "NONE",
            "classifier": "APPLICATION",
            "tags": [parsed["name"].lower().replace("-", "_")],
            "sbom_file": sbom_path,
        }

        leaf_components.append(component)

    return leaf_components
