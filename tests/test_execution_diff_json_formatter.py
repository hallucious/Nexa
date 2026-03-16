"""
tests/test_execution_diff_json_formatter.py

Tests for format_diff_json (Step185).
"""
from __future__ import annotations

import json

import pytest

from src.engine.execution_diff_formatter import format_diff_json
from src.engine.execution_diff_model import (
    CHANGE_TYPE_ADDED, CHANGE_TYPE_MODIFIED, CHANGE_TYPE_REMOVED,
    RUN_DIFF_STATUS_CHANGED, RUN_DIFF_STATUS_IDENTICAL,
    ArtifactDiff, ContextDiff, DiffSummary, NodeDiff, RunDiff,
)


def _empty() -> RunDiff:
    return RunDiff(left_run_id="r1", right_run_id="r2", status=RUN_DIFF_STATUS_IDENTICAL)


def _full() -> RunDiff:
    return RunDiff(
        left_run_id="r1", right_run_id="r2", status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[
            NodeDiff(node_id="n1", change_type=CHANGE_TYPE_MODIFIED,
                     left_status="success", right_status="failure",
                     left_output_ref="r1/n1", right_output_ref="r2/n1",
                     artifact_ids_added=["art_new"], artifact_ids_removed=[], artifact_ids_changed=["art_mod"]),
            NodeDiff(node_id="n2", change_type=CHANGE_TYPE_ADDED),
        ],
        artifact_diffs=[
            ArtifactDiff(artifact_id="art_1", change_type=CHANGE_TYPE_MODIFIED,
                         left_hash="old", right_hash="new",
                         left_kind="provider_output", right_kind="provider_output"),
        ],
        context_diffs=[
            ContextDiff(context_key="input.text.value", change_type=CHANGE_TYPE_MODIFIED,
                        left_value="hello", right_value="world"),
        ],
        summary=DiffSummary(
            nodes_added=1, nodes_removed=0, nodes_changed=1,
            artifacts_added=0, artifacts_removed=0, artifacts_changed=1,
            context_keys_changed=1,
        ),
    )


# --- Return type ---

def test_returns_dict():
    assert isinstance(format_diff_json(_empty()), dict)


# --- Top-level keys ---

def test_has_required_top_level_keys():
    d = format_diff_json(_full())
    for key in ("status", "summary", "nodes", "artifacts", "context"):
        assert key in d, f"missing key: {key}"


# --- Status ---

def test_status_identical():
    assert format_diff_json(_empty())["status"] == RUN_DIFF_STATUS_IDENTICAL


def test_status_changed():
    assert format_diff_json(_full())["status"] == RUN_DIFF_STATUS_CHANGED


# --- Summary ---

def test_summary_is_dict():
    assert isinstance(format_diff_json(_full())["summary"], dict)


def test_summary_all_fields_present():
    s = format_diff_json(_full())["summary"]
    for field in ("nodes_added", "nodes_removed", "nodes_changed",
                  "artifacts_added", "artifacts_removed", "artifacts_changed",
                  "trace_keys_changed", "context_keys_changed"):
        assert field in s


def test_summary_values_match():
    s = format_diff_json(_full())["summary"]
    assert s["nodes_added"] == 1
    assert s["nodes_changed"] == 1
    assert s["artifacts_changed"] == 1
    assert s["context_keys_changed"] == 1


def test_summary_zeros_for_identical():
    s = format_diff_json(_empty())["summary"]
    assert all(v == 0 for v in s.values())


# --- Nodes list ---

def test_nodes_is_list():
    assert isinstance(format_diff_json(_full())["nodes"], list)


def test_nodes_count():
    assert len(format_diff_json(_full())["nodes"]) == 2


def test_nodes_empty_for_identical():
    assert format_diff_json(_empty())["nodes"] == []


def test_node_has_required_fields():
    node = format_diff_json(_full())["nodes"][0]
    for field in ("node_id", "change_type", "left_status", "right_status",
                  "left_output_ref", "right_output_ref",
                  "artifact_ids_added", "artifact_ids_removed", "artifact_ids_changed"):
        assert field in node


def test_node_values():
    node = format_diff_json(_full())["nodes"][0]
    assert node["node_id"] == "n1"
    assert node["change_type"] == CHANGE_TYPE_MODIFIED
    assert node["left_status"] == "success"
    assert node["right_status"] == "failure"
    assert "art_new" in node["artifact_ids_added"]
    assert "art_mod" in node["artifact_ids_changed"]


# --- Artifacts list ---

def test_artifacts_is_list():
    assert isinstance(format_diff_json(_full())["artifacts"], list)


def test_artifacts_count():
    assert len(format_diff_json(_full())["artifacts"]) == 1


def test_artifact_has_required_fields():
    art = format_diff_json(_full())["artifacts"][0]
    for field in ("artifact_id", "change_type", "left_hash", "right_hash", "left_kind", "right_kind"):
        assert field in art


def test_artifact_values():
    art = format_diff_json(_full())["artifacts"][0]
    assert art["artifact_id"] == "art_1"
    assert art["left_hash"] == "old"
    assert art["right_hash"] == "new"


# --- Context list ---

def test_context_is_list():
    assert isinstance(format_diff_json(_full())["context"], list)


def test_context_count():
    assert len(format_diff_json(_full())["context"]) == 1


def test_context_has_required_fields():
    cd = format_diff_json(_full())["context"][0]
    for field in ("context_key", "change_type", "left_value", "right_value"):
        assert field in cd


def test_context_values():
    cd = format_diff_json(_full())["context"][0]
    assert cd["context_key"] == "input.text.value"
    assert cd["left_value"] == "hello"
    assert cd["right_value"] == "world"


# --- JSON serialisable ---

def test_json_serialisable():
    d = format_diff_json(_full())
    s = json.dumps(d)
    assert isinstance(s, str)
    assert json.loads(s)["status"] == RUN_DIFF_STATUS_CHANGED


def test_json_serialisable_identical():
    d = format_diff_json(_empty())
    assert json.loads(json.dumps(d))["status"] == RUN_DIFF_STATUS_IDENTICAL


# --- Determinism ---

def test_deterministic():
    d = _full()
    assert format_diff_json(d) == format_diff_json(d)
