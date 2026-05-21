"""Auto-tagging helpers for Dependency Track projects.

Single source of truth for the four canonical managed tag prefixes
(``name:``, ``version:``, ``parent:``, ``lifecycle:``).
"""

from typing import Optional, List

LIFECYCLE_PREFIXES = ("alpha", "beta", "dev", "preview", "rc")
GA_TAG = "lifecycle:GA"

_MANAGED_PREFIXES = ("name:", "version:", "parent:", "lifecycle:")


def compute_auto_tags(
    name: str,
    version: Optional[str],
    parent_name: Optional[str],
) -> List[str]:
    """Compute the four canonical auto-tags for a project.

    Args:
        name: Project name.
        version: Project version, or None.
        parent_name: Parent project name, or None.

    Returns:
        List of tag strings — always includes ``name:`` and ``lifecycle:``,
        plus ``version:`` and ``parent:`` when those values are provided.
    """
    tags: List[str] = []
    tags.append(f"name:{_normalize(name)}")
    if version:
        tags.append(f"version:{_normalize(version)}")
    if parent_name:
        tags.append(f"parent:{_normalize(parent_name)}")
    tags.append(_lifecycle_tag(version))
    return tags


def merge_auto_tags(existing: List[str], auto: List[str]) -> List[str]:
    """Merge computed auto-tags into an existing tag list.

    Strips any existing managed-prefix tags (``name:``, ``version:``,
    ``parent:``, ``lifecycle:``) and appends the freshly computed ones,
    preserving every other tag.  The result is deduplicated while
    preserving insertion order.

    Args:
        existing: Current list of tag strings on the project.
        auto: Tags produced by :func:`compute_auto_tags`.

    Returns:
        Deduplicated merged tag list.
    """
    preserved = [t for t in existing if not _is_managed(t)]
    merged = preserved + auto
    seen: set = set()
    result: List[str] = []
    for tag in merged:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    """Lowercase and replace hyphens with underscores."""
    return value.lower().replace("-", "_")


def _lifecycle_tag(version: Optional[str]) -> str:
    """Return the appropriate ``lifecycle:`` tag for *version*.

    Performs a case-insensitive substring scan in LIFECYCLE_PREFIXES order;
    first match wins.  Returns ``lifecycle:GA`` when no keyword is found or
    when *version* is None.
    """
    if version:
        lower = version.lower()
        for prefix in LIFECYCLE_PREFIXES:
            if prefix in lower:
                return f"lifecycle:{prefix}"
    return GA_TAG


def _is_managed(tag: str) -> bool:
    """Return True when *tag* belongs to one of the four managed prefixes."""
    return any(tag.startswith(p) for p in _MANAGED_PREFIXES)
