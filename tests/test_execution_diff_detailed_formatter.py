"""
tests/test_execution_diff_detailed_formatter.py

Tests for the detailed Execution Diff Formatter (Step184).
"""
from __future__ import annotations

import pytest

from src.engine.execution_diff_formatter import (
    format_diff,
    format_diff_details,
    format_diff_summary,
)
from src.engine.execution_diff_model import (
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_REMOVED,
    RUN_DIFF_STATUS_CHANGED,
    RUN_DIFF_STATUS_IDENTICAL,
    ArtifactDiff,
    ContextDiff,
    DiffSummary,
    NodeDiff,
    RunDiff,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _empty_diff() -> RunDiff:
    return RunDiff(left_run_id="r1", right_run_id="r2", status=RUN_DIFF_STATUS_IDENTICAL)


def _full_diff() -> RunDiff:
    return RunDiff(
        left_run_id="r1",
        right_run_id="r2",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[
            NodeDiff(
                node_id="n1",
                change_type=CHANGE_TYPE_MODIFIED,
                left_status="success",
                right_status="failure",
                left_output_ref="r1/n1",
                right_output_ref="r2/n1",
                artifact_ids_added=["art_new"],
                artifact_ids_removed=["art_old"],
                artifact_ids_changed=["art_mod"],
            ),
            NodeDiff(node_id="n2", change_type=CHANGE_TYPE_ADDED, right_status="success"),
            NodeDiff(node_id="n3", change_type=CHANGE_TYPE_REMOVED, left_status="success"),
        ],
        artifact_diffs=[
            ArtifactDiff(
                artifact_id="art_1",
                change_type=CHANGE_TYPE_MODIFIED,
                left_hash="old",
                right_hash="new",
                left_kind="provider_output",
                right_kind="provider_output",
            ),
            ArtifactDiff(artifact_id="art_2", change_type=CHANGE_TYPE_ADDED, right_hash="h2"),
        ],
        context_diffs=[
            ContextDiff(
                context_key="input.text.value",
                change_type=CHANGE_TYPE_MODIFIED,
                left_value="hello",
                right_value="world",
            ),
            ContextDiff(
                context_key="output.summary.value",
                change_type=CHANGE_TYPE_ADDED,
                right_value="new",
            ),
        ],
        summary=DiffSummary(
            nodes_added=1, nodes_removed=1, nodes_changed=1,
            artifacts_added=1, artifacts_removed=0, artifacts_changed=1,
            context_keys_changed=2,
        ),
    )


# ---------------------------------------------------------------------------
# format_diff_summary (existing, must remain unchanged)
# ---------------------------------------------------------------------------

def test_summary_still_returns_string():
    assert isinstance(format_diff_summary(_empty_diff()), str)


def test_summary_identical():
    out = format_diff_summary(_empty_diff())
    assert "status: identical" in out


def test_summary_fields_present():
    out = format_diff_summary(_full_diff())
    assert "Execution Diff" in out
    assert "status:" in out
    assert "nodes:" in out
    assert "artifacts:" in out
    assert "context_keys_changed:" in out


# ---------------------------------------------------------------------------
# format_diff_details — node changes
# ---------------------------------------------------------------------------

def test_details_node_section_header():
    out = format_diff_details(_full_diff())
    assert "Node Changes" in out


def test_details_node_change_type_and_id():
    out = format_diff_details(_full_diff())
    assert "[modified] n1" in out
    assert "[added] n2" in out
    assert "[removed] n3" in out


def test_details_node_status_shown():
    out = format_diff_details(_full_diff())
    assert "status: success -> failure" in out


def test_details_node_output_ref_shown():
    out = format_diff_details(_full_diff())
    assert "output_ref: r1/n1 -> r2/n1" in out


def test_details_node_artifact_ids_shown():
    out = format_diff_details(_full_diff())
    assert "art_new" in out
    assert "art_old" in out
    assert "art_mod" in out


# ---------------------------------------------------------------------------
# format_diff_details — artifact changes
# ---------------------------------------------------------------------------

def test_details_artifact_section_header():
    out = format_diff_details(_full_diff())
    assert "Artifact Changes" in out


def test_details_artifact_change_type_and_id():
    out = format_diff_details(_full_diff())
    assert "[modified] art_1" in out
    assert "[added] art_2" in out


def test_details_artifact_hash_shown():
    out = format_diff_details(_full_diff())
    assert "hash: old -> new" in out


def test_details_artifact_kind_shown():
    out = format_diff_details(_full_diff())
    assert "kind: provider_output -> provider_output" in out


# ---------------------------------------------------------------------------
# format_diff_details — context changes
# ---------------------------------------------------------------------------

def test_details_context_section_header():
    out = format_diff_details(_full_diff())
    assert "Context Changes" in out


def test_details_context_key_and_change_type():
    out = format_diff_details(_full_diff())
    assert "[modified] input.text.value" in out
    assert "[added] output.summary.value" in out


def test_details_context_values_shown():
    out = format_diff_details(_full_diff())
    assert "'hello'" in out
    assert "'world'" in out


# ---------------------------------------------------------------------------
# format_diff_details — identical run (empty details)
# ---------------------------------------------------------------------------

def test_details_empty_for_identical_run():
    out = format_diff_details(_empty_diff())
    assert out == ""


# ---------------------------------------------------------------------------
# format_diff — combined
# ---------------------------------------------------------------------------

def test_format_diff_returns_string():
    assert isinstance(format_diff(_empty_diff()), str)


def test_format_diff_identical_no_detail_sections():
    out = format_diff(_empty_diff())
    assert "Node Changes" not in out
    assert "Artifact Changes" not in out
    assert "Context Changes" not in out


def test_format_diff_changed_contains_summary_and_details():
    out = format_diff(_full_diff())
    assert "Execution Diff" in out
    assert "status: changed" in out
    assert "Node Changes" in out
    assert "Artifact Changes" in out
    assert "Context Changes" in out


def test_format_diff_summary_before_details():
    out = format_diff(_full_diff())
    summary_pos = out.index("Execution Diff")
    node_pos = out.index("Node Changes")
    assert summary_pos < node_pos


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_format_diff_is_deterministic():
    d = _full_diff()
    assert format_diff(d) == format_diff(d)


def test_format_diff_details_is_deterministic():
    d = _full_diff()
    assert format_diff_details(d) == format_diff_details(d)
