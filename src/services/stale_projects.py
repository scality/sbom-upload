"""Staleness decision helpers for Dependency Track projects.

All functions are pure (no I/O) so they are easy to unit-test in isolation.
"""

from typing import Dict, Any, List, Optional, Tuple

STALE_THRESHOLD_DAYS = 15
_MILLIS_PER_DAY = 86_400_000

_GA_TAG = "lifecycle:GA"
_KEEP_ACTIVE_TAG = "keep-active"


def is_stale(
    project: Dict[str, Any],
    now_ms: int,
    threshold_days: int = STALE_THRESHOLD_DAYS,
) -> Tuple[bool, str]:
    """Determine whether a project should be deactivated.

    Skip conditions for **leaf** projects (in evaluation order):
    1. Already inactive
    2. Tags contain ``lifecycle:GA``
    3. Tags contain ``keep-active``
    4. Age ≤ threshold (projects with a null ``lastBomImport`` are considered
       infinitely old and therefore always stale)

    Note: collection parents use a different rule (no active children) and are
    not evaluated through this function.

    Args:
        project: Raw DT project dict from the API.
        now_ms: Current time as Unix epoch milliseconds.
        threshold_days: Days without a BOM import to be considered stale.

    Returns:
        ``(stale, skip_reason)`` — when *stale* is ``False``, *skip_reason*
        is a short string explaining why; when *stale* is ``True``,
        *skip_reason* is an empty string.
    """
    if not project.get("active", True):
        return False, "already_inactive"

    tag_names = {t["name"] for t in project.get("tags", [])}
    if _GA_TAG in tag_names:
        return False, "lifecycle_GA"
    if _KEEP_ACTIVE_TAG in tag_names:
        return False, "keep_active"

    last_bom_import = project.get("lastBomImport")
    if last_bom_import is not None:
        age_days = (now_ms - last_bom_import) / _MILLIS_PER_DAY
        if age_days <= threshold_days:
            return False, "not_stale"

    # null lastBomImport → never imported → always stale
    return True, ""


def partition_by_collection(
    projects: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separate leaf projects from collection parents.

    A project is a *collection parent* when its ``collectionLogic`` field is
    set to a value other than ``"NONE"`` (or absent / null).

    Args:
        projects: List of raw DT project dicts.

    Returns:
        ``(leaves, parents)`` where *parents* have a non-NONE collectionLogic.
    """
    leaves: List[Dict[str, Any]] = []
    parents: List[Dict[str, Any]] = []
    for proj in projects:
        logic = proj.get("collectionLogic") or "NONE"
        if logic == "NONE":
            leaves.append(proj)
        else:
            parents.append(proj)
    return leaves, parents


def build_summary(
    deactivated: List[Dict[str, Any]],
    skipped: List[Tuple[Dict[str, Any], str]],
    dry_run: bool,
) -> Dict[str, Any]:
    """Build a JSON-serialisable summary of the deactivation run.

    Args:
        deactivated: Projects that were (or would be) deactivated.
        skipped: ``(project, reason)`` pairs for skipped projects.
        dry_run: Whether this was a dry-run.

    Returns:
        Summary dict with ``dry_run``, ``deactivated``, ``skipped``,
        and ``counts`` keys.
    """
    return {
        "dry_run": dry_run,
        "deactivated": [
            {
                "uuid": p.get("uuid"),
                "name": p.get("name"),
                "version": p.get("version"),
            }
            for p in deactivated
        ],
        "skipped": [
            {
                "uuid": p.get("uuid"),
                "name": p.get("name"),
                "version": p.get("version"),
                "reason": reason,
            }
            for p, reason in skipped
        ],
        "counts": {
            "deactivated": len(deactivated),
            "skipped": len(skipped),
        },
    }
