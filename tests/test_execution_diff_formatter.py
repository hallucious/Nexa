"""
tests/test_execution_diff_formatter.py

Tests for the Execution Diff Formatter (Step183).

Covers:
1. formatter returns a string
2. identical diff formatting
3. changed diff formatting
4. all required summary fields present in output
5. output is deterministic for same input
"""
from __future__ import annotations

import pytest

from src.engine.execution_diff_formatter import format_diff_summary
from src.engine.execution_diff_model import (
    ArtifactDiff,
    ContextDiff,
    DiffSummary,
    NodeDiff,
    RunDiff,
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_MODIFIED,
    RUN_DIFF_STATUS_IDENTICAL,
    RUN_DIFF_STATUS_CHANGED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identical_diff() -> RunDiff:
    return RunDiff(
        left_run_id="r1",
        right_run_id="r2",
        status=RUN_DIFF_STATUS_IDENTICAL,
    )


def _changed_diff() -> RunDiff:
    return RunDiff(
        left_run_id="r1",
        right_run_id="r2",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[
            NodeDiff(node_id="n1", change_type=CHANGE_TYPE_MODIFIED),
            NodeDiff(node_id="n2", change_type=CHANGE_TYPE_ADDED),
        ],
        artifact_diffs=[
            ArtifactDiff(artifact_id="art_1", change_type=CHANGE_TYPE_ADDED),
        ],
        context_diffs=[
            ContextDiff(context_key="input.text.value", change_type=CHANGE_TYPE_MODIFIED),
            ContextDiff(context_key="output.summary.value", change_type=CHANGE_TYPE_ADDED),
        ],
        summary=DiffSummary(
            nodes_added=1,
            nodes_removed=0,
            nodes_changed=1,
            artifacts_added=1,
            artifacts_removed=0,
            artifacts_changed=0,
            context_keys_changed=2,
        ),
    )


# ---------------------------------------------------------------------------
# 1. Formatter returns a string
# ---------------------------------------------------------------------------

def test_format_diff_summary_returns_string():
    diff = _identical_diff()
    result = format_diff_summary(diff)
    assert isinstance(result, str)


def test_format_diff_summary_non_empty():
    diff = _identical_diff()
    result = format_diff_summary(diff)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 2. Identical diff formatting
# ---------------------------------------------------------------------------

def test_format_identical_contains_status():
    result = format_diff_summary(_identical_diff())
    assert "status: identical" in result


def test_format_identical_contains_title():
    result = format_diff_summary(_identical_diff())
    assert "Execution Diff" in result


def test_format_identical_zero_counts():
    result = format_diff_summary(_identical_diff())
    assert "added=0" in result
    assert "removed=0" in result
    assert "changed=0" in result
    assert "context_keys_changed: 0" in result


# ---------------------------------------------------------------------------
# 3. Changed diff formatting
# ---------------------------------------------------------------------------

def test_format_changed_contains_status():
    result = format_diff_summary(_changed_diff())
    assert "status: changed" in result


def test_format_changed_nodes_line():
    result = format_diff_summary(_changed_diff())
    assert "nodes: added=1 removed=0 changed=1" in result


def test_format_changed_artifacts_line():
    result = format_diff_summary(_changed_diff())
    assert "artifacts: added=1 removed=0 changed=0" in result


def test_format_changed_context_keys():
    result = format_diff_summary(_changed_diff())
    assert "context_keys_changed: 2" in result


# ---------------------------------------------------------------------------
# 4. All required summary fields present
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("diff", [_identical_diff(), _changed_diff()])
def test_required_fields_present(diff):
    result = format_diff_summary(diff)
    assert "Execution Diff" in result
    assert "status:" in result
    assert "nodes:" in result
    assert "added=" in result
    assert "removed=" in result
    assert "changed=" in result
    assert "artifacts:" in result
    assert "context_keys_changed:" in result


# ---------------------------------------------------------------------------
# 5. Output is deterministic for same input
# ---------------------------------------------------------------------------

def test_format_is_deterministic():
    diff = _changed_diff()
    assert format_diff_summary(diff) == format_diff_summary(diff)


def test_format_identical_diffs_produce_same_output():
    d1 = _identical_diff()
    d2 = _identical_diff()
    assert format_diff_summary(d1) == format_diff_summary(d2)


def test_format_changed_diffs_produce_same_output():
    d1 = _changed_diff()
    d2 = _changed_diff()
    assert format_diff_summary(d1) == format_diff_summary(d2)


# ---------------------------------------------------------------------------
# Exact output shape
# ---------------------------------------------------------------------------

def test_format_output_line_order():
    """Verify the exact output structure."""
    diff = _identical_diff()
    result = format_diff_summary(diff)
    lines = result.splitlines()
    assert lines[0] == "Execution Diff"
    assert lines[1].startswith("status:")
    assert lines[2].startswith("nodes:")
    assert lines[3].startswith("artifacts:")
    assert lines[4].startswith("context_keys_changed:")
