"""Version comparison utilities."""

import re
from typing import List, Tuple, Optional

# Match semantic version pattern with optional pre-release
SEMVER_PATTERN = (
    r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?"
    r"(?:[-.]?(alpha|beta|rc|preview|dev|snapshot)(?:[-.]?(\d+))?)?"
)


def parse_version(version_str: str) -> Tuple[int, int, int, str, int]:
    """
    Parse a version string into comparable components.
    Args:
        version_str (str): Version string to parse
    Returns:
        Tuple[int, int, int, str, int]:
        Parsed components (major, minor, patch, prerelease, prerelease_num)
    Raises:
        None
    """
    if not version_str:
        return (0, 0, 0, "", 0)

    # Clean version string - remove 'v' prefix if present
    clean_version = version_str.strip().lower()
    if clean_version.startswith("v"):
        clean_version = clean_version[1:]

    # Handle special cases like "latest", "main", "master"
    if clean_version in ["latest", "main", "master", "head"]:
        return (999, 999, 999, "", 0)

    match = re.match(SEMVER_PATTERN, clean_version)

    if not match:
        # If no match, try to extract numbers
        numbers = re.findall(r"\d+", clean_version)
        if numbers:
            major = int(numbers[0]) if len(numbers) > 0 else 0
            minor = int(numbers[1]) if len(numbers) > 1 else 0
            patch = int(numbers[2]) if len(numbers) > 2 else 0
            return (major, minor, patch, "unknown", 0)
        return (0, 0, 0, "unknown", 0)

    major = int(match.group(1))
    minor = int(match.group(2)) if match.group(2) else 0
    patch = int(match.group(3)) if match.group(3) else 0
    prerelease = match.group(4) if match.group(4) else ""
    prerelease_num = int(match.group(5)) if match.group(5) else 0

    return (major, minor, patch, prerelease, prerelease_num)


def compare_versions(  # pylint: disable=too-many-return-statements, too-many-branches
    version1: str, version2: str
) -> int:
    """
    Compare two version strings.
    Args:
        version1 (str): First version string
        version2 (str): Second version string
    Returns:
        -1 if version1 < version2
        0 if version1 == version2
        1 if version1 > version2
    """
    v1_parts = parse_version(version1)
    v2_parts = parse_version(version2)

    # Compare major, minor, patch
    for i in range(3):
        if v1_parts[i] < v2_parts[i]:
            return -1
        if v1_parts[i] > v2_parts[i]:
            return 1

    # If base versions are equal, compare pre-release
    v1_prerelease = v1_parts[3]
    v2_prerelease = v2_parts[3]

    # No pre-release is considered higher than any pre-release
    if not v1_prerelease and not v2_prerelease:
        return 0
    if not v1_prerelease and v2_prerelease:
        return 1
    if v1_prerelease and not v2_prerelease:
        return -1

    # Both have pre-release, compare them
    prerelease_order = ["dev", "snapshot", "alpha", "beta", "rc", "preview"]

    if v1_prerelease in prerelease_order and v2_prerelease in prerelease_order:
        v1_idx = prerelease_order.index(v1_prerelease)
        v2_idx = prerelease_order.index(v2_prerelease)

        if v1_idx < v2_idx:
            return -1
        if v1_idx > v2_idx:
            return 1

        # Same pre-release type, compare numbers
        v1_num = v1_parts[4]
        v2_num = v2_parts[4]
        if v1_num < v2_num:
            return -1
        if v1_num > v2_num:
            return 1
        return 0

    # Fallback to string comparison for unknown pre-release types
    if v1_prerelease < v2_prerelease:
        return -1
    if v1_prerelease > v2_prerelease:
        return 1
    return 0


def is_latest_version(version: str, version_list: List[str]) -> bool:
    """
    Check if a version is the latest in a list of versions.
    Args:
        version (str): Version to check
        version_list (List[str]): List of other versions to compare against
    Returns:
        bool: True if version is the highest in the list, False otherwise
    """
    if not version_list:
        return True

    for other_version in version_list:
        if compare_versions(other_version, version) > 0:
            return False

    return True


def get_latest_version(versions: List[str]) -> Optional[str]:
    """
    Get the latest (highest) version from a list of version strings.
    Args:
        versions (List[str]): List of version strings
    Returns:
        Optional[str]: The highest version string, or None if list is empty
    """
    if not versions:
        return None

    return max(versions, key=parse_version)
