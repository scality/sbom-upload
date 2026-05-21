"""Unit tests for src/services/tagging.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from services.tagging import (
    compute_auto_tags,
    merge_auto_tags,
    GA_TAG,
    LIFECYCLE_PREFIXES,
)


# ---------------------------------------------------------------------------
# compute_auto_tags — lifecycle detection
# ---------------------------------------------------------------------------


def test_lifecycle_ga_no_version():
    tags = compute_auto_tags("myapp", None, None)
    assert "lifecycle:GA" in tags
    assert not any(t.startswith("version:") for t in tags)


def test_lifecycle_ga_plain_version():
    tags = compute_auto_tags("myapp", "1.2.3", None)
    assert "lifecycle:GA" in tags


@pytest.mark.parametrize("keyword", list(LIFECYCLE_PREFIXES))
def test_lifecycle_keyword(keyword):
    tags = compute_auto_tags("svc", f"1.0.0-{keyword}.1", None)
    assert f"lifecycle:{keyword}" in tags
    assert "lifecycle:GA" not in tags


def test_lifecycle_first_match_wins_alpha_before_beta():
    """alpha appears before beta in LIFECYCLE_PREFIXES — alpha must win."""
    tags = compute_auto_tags("svc", "1.0.0-alpha-beta", None)
    assert "lifecycle:alpha" in tags
    assert "lifecycle:beta" not in tags


def test_lifecycle_first_match_wins_dev_before_preview():
    """dev appears before preview in LIFECYCLE_PREFIXES — dev must win."""
    tags = compute_auto_tags("svc", "1.0.0-dev-preview", None)
    assert "lifecycle:dev" in tags
    assert "lifecycle:preview" not in tags


def test_lifecycle_case_insensitive():
    tags = compute_auto_tags("svc", "1.0.0-RC.1", None)
    assert "lifecycle:rc" in tags


# ---------------------------------------------------------------------------
# compute_auto_tags — name / version / parent normalization
# ---------------------------------------------------------------------------


def test_name_tag_present():
    tags = compute_auto_tags("my-app", "1.0.0", None)
    assert "name:my_app" in tags


def test_version_tag_dash_normalization():
    tags = compute_auto_tags("svc", "1.0.0-rc.1", None)
    assert "version:1.0.0_rc.1" in tags


def test_version_tag_absent_when_no_version():
    tags = compute_auto_tags("svc", None, None)
    assert not any(t.startswith("version:") for t in tags)


def test_parent_tag_present():
    tags = compute_auto_tags("child", "1.0.0", "my-parent")
    assert "parent:my_parent" in tags


def test_parent_tag_absent_when_no_parent():
    tags = compute_auto_tags("child", "1.0.0", None)
    assert not any(t.startswith("parent:") for t in tags)


def test_parent_tag_normalization():
    tags = compute_auto_tags("svc", "1.0", "Big-Parent")
    assert "parent:big_parent" in tags


def test_all_four_tags_when_fully_specified():
    tags = compute_auto_tags("my-svc", "2.0.0-beta.1", "my-parent")
    prefixes = {"name:", "version:", "parent:", "lifecycle:"}
    found = {t.split(":")[0] + ":" for t in tags}
    assert prefixes == found


# ---------------------------------------------------------------------------
# merge_auto_tags — deduplication & replacement
# ---------------------------------------------------------------------------


def test_merge_replaces_lifecycle():
    existing = ["lifecycle:alpha", "custom-tag"]
    auto = compute_auto_tags("svc", "1.0.0", None)  # lifecycle:GA
    result = merge_auto_tags(existing, auto)
    assert "lifecycle:GA" in result
    assert "lifecycle:alpha" not in result


def test_merge_replaces_name():
    existing = ["name:old_name", "team:backend"]
    auto = compute_auto_tags("new-name", "1.0.0", None)
    result = merge_auto_tags(existing, auto)
    assert "name:new_name" in result
    assert "name:old_name" not in result


def test_merge_preserves_user_tags():
    existing = ["team:backend", "env:prod", "lifecycle:alpha"]
    auto = compute_auto_tags("svc", "1.0.0", None)
    result = merge_auto_tags(existing, auto)
    assert "team:backend" in result
    assert "env:prod" in result


def test_merge_no_duplicates():
    auto = compute_auto_tags("svc", "1.0.0", None)
    # Merge same auto tags twice
    result = merge_auto_tags(auto, auto)
    assert len(result) == len(set(result))


def test_merge_idempotent():
    """Running merge twice should produce the same result."""
    existing = ["custom", "lifecycle:beta"]
    auto = compute_auto_tags("svc", "2.0.0", "parent-svc")
    first = merge_auto_tags(existing, auto)
    second = merge_auto_tags(first, auto)
    assert first == second


def test_merge_removes_version_tag_when_rerun():
    existing = ["version:1.0.0", "lifecycle:GA", "name:svc"]
    auto = compute_auto_tags("svc", "2.0.0", None)
    result = merge_auto_tags(existing, auto)
    assert "version:1.0.0" not in result
    assert "version:2.0.0" in result


def test_merge_removes_parent_tag_when_rerun():
    existing = ["parent:old_parent"]
    auto = compute_auto_tags("svc", "1.0.0", "new-parent")
    result = merge_auto_tags(existing, auto)
    assert "parent:old_parent" not in result
    assert "parent:new_parent" in result


def test_merge_empty_existing():
    result = merge_auto_tags([], compute_auto_tags("svc", "1.0.0", None))
    assert "name:svc" in result
    assert "lifecycle:GA" in result
