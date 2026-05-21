"""Unit tests for src/services/stale_projects.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from services.stale_projects import (
    is_stale,
    partition_by_collection,
    build_summary,
    STALE_THRESHOLD_DAYS,
)

_DAY_MS = 86_400_000
_NOW_MS = 1_700_000_000_000  # fixed reference timestamp


def _project(**kwargs):
    """Minimal active project dict with sensible defaults."""
    base = {
        "uuid": "test-uuid",
        "name": "test-project",
        "version": "1.0.0",
        "active": True,
        "isLatest": False,
        "lastBomImport": _NOW_MS - 20 * _DAY_MS,  # 20 days old → stale by default
        "tags": [],
        "collectionLogic": "NONE",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# is_stale — skip conditions
# ---------------------------------------------------------------------------


def test_skip_already_inactive():
    stale, reason = is_stale(_project(active=False), _NOW_MS)
    assert stale is False
    assert reason == "already_inactive"


def test_is_latest_is_still_stale():
    """isLatest=true no longer protects a project from being deactivated."""
    stale, reason = is_stale(_project(isLatest=True), _NOW_MS)
    assert stale is True
    assert reason == ""


def test_null_bom_import_is_stale():
    """A project that was never imported has no protection — always stale."""
    stale, reason = is_stale(_project(lastBomImport=None), _NOW_MS)
    assert stale is True
    assert reason == ""


def test_skip_lifecycle_ga_tag():
    proj = _project(tags=[{"name": "lifecycle:GA"}])
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "lifecycle_GA"


def test_skip_keep_active_tag():
    proj = _project(tags=[{"name": "keep-active"}])
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "keep_active"


def test_skip_not_stale_recent():
    proj = _project(lastBomImport=_NOW_MS - 10 * _DAY_MS)
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "not_stale"


def test_skip_exactly_on_threshold():
    """Age == threshold is NOT stale (strict >)."""
    proj = _project(lastBomImport=_NOW_MS - STALE_THRESHOLD_DAYS * _DAY_MS)
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "not_stale"


def test_stale_old_project():
    stale, reason = is_stale(_project(), _NOW_MS)
    assert stale is True
    assert reason == ""


def test_custom_threshold():
    proj = _project(lastBomImport=_NOW_MS - 20 * _DAY_MS)
    # With threshold=30, a 20-day-old project is NOT stale
    stale, reason = is_stale(proj, _NOW_MS, threshold_days=30)
    assert stale is False
    assert reason == "not_stale"
    # With threshold=10, it IS stale
    stale2, _ = is_stale(proj, _NOW_MS, threshold_days=10)
    assert stale2 is True


def test_ga_tag_takes_priority_over_staleness():
    """lifecycle:GA overrides even a very old project."""
    proj = _project(
        lastBomImport=_NOW_MS - 365 * _DAY_MS,
        tags=[{"name": "lifecycle:GA"}, {"name": "extra"}],
    )
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "lifecycle_GA"


def test_ga_tag_takes_priority_over_null_bom_import():
    """lifecycle:GA protects a project even when lastBomImport is null."""
    proj = _project(lastBomImport=None, tags=[{"name": "lifecycle:GA"}])
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "lifecycle_GA"


def test_keep_active_takes_priority_over_null_bom_import():
    proj = _project(lastBomImport=None, tags=[{"name": "keep-active"}])
    stale, reason = is_stale(proj, _NOW_MS)
    assert stale is False
    assert reason == "keep_active"


def test_skip_order_inactive_checked_first():
    """already_inactive is checked before anything else."""
    proj = _project(active=False, isLatest=True, tags=[{"name": "lifecycle:GA"}])
    _, reason = is_stale(proj, _NOW_MS)
    assert reason == "already_inactive"


# ---------------------------------------------------------------------------
# partition_by_collection
# ---------------------------------------------------------------------------


def test_partition_leaves_have_none_logic():
    projects = [
        _project(uuid="a", collectionLogic="NONE"),
        _project(uuid="b", collectionLogic="AGGREGATE_DIRECT_CHILDREN"),
        _project(uuid="c", collectionLogic="AGGREGATE_LATEST_VERSION_CHILDREN"),
        _project(uuid="d"),  # missing key → treated as NONE
    ]
    leaves, parents = partition_by_collection(projects)
    leaf_uuids = {p["uuid"] for p in leaves}
    parent_uuids = {p["uuid"] for p in parents}
    assert leaf_uuids == {"a", "d"}
    assert parent_uuids == {"b", "c"}


def test_partition_null_collection_logic():
    """collectionLogic=None is treated the same as 'NONE'."""
    proj = _project(collectionLogic=None)
    leaves, parents = partition_by_collection([proj])
    assert len(leaves) == 1
    assert len(parents) == 0


def test_partition_empty_list():
    leaves, parents = partition_by_collection([])
    assert leaves == []
    assert parents == []


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------


def test_build_summary_structure():
    deactivated = [_project(uuid="u1", name="p1", version="1.0")]
    skipped = [(_project(uuid="u2", name="p2"), "is_latest")]
    summary = build_summary(deactivated, skipped, dry_run=False)

    assert summary["dry_run"] is False
    assert summary["counts"]["deactivated"] == 1
    assert summary["counts"]["skipped"] == 1
    assert summary["deactivated"][0]["uuid"] == "u1"
    assert summary["skipped"][0]["reason"] == "is_latest"


def test_build_summary_dry_run_flag():
    summary = build_summary([], [], dry_run=True)
    assert summary["dry_run"] is True
    assert summary["counts"]["deactivated"] == 0
    assert summary["counts"]["skipped"] == 0


def test_build_summary_preserves_name_version():
    deactivated = [{"uuid": "x", "name": "svc", "version": "2.0"}]
    summary = build_summary(deactivated, [], dry_run=False)
    entry = summary["deactivated"][0]
    assert entry["name"] == "svc"
    assert entry["version"] == "2.0"
