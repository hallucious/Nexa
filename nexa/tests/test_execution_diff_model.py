"""
tests/test_execution_diff_model.py

Tests for the Execution Diff data model (Step180).

Covers:
1. RunDiff creation
2. NodeDiff creation
3. ArtifactDiff creation
4. TraceDiff creation
5. ContextDiff creation
6. Serialization to dict
7. JSON compatibility
8. Empty diff scenario
9. Modified diff scenario
"""
from __future__ import annotations

import json

import pytest

from src.engine.execution_diff_model import (
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_REMOVED,
    CHANGE_TYPE_UNCHANGED,
    RUN_DIFF_STATUS_CHANGED,
    RUN_DIFF_STATUS_IDENTICAL,
    RUN_DIFF_STATUS_INCOMPLETE,
    VALID_CHANGE_TYPES,
    VALID_RUN_DIFF_STATUSES,
    ArtifactDiff,
    ContextDiff,
    DiffSummary,
    NodeDiff,
    RunDiff,
    TraceDiff,
)


# ---------------------------------------------------------------------------
# 1. DiffSummary creation
# ---------------------------------------------------------------------------

def test_diff_summary_defaults_are_zero():
    s = DiffSummary()
    assert s.nodes_added == 0
    assert s.nodes_removed == 0
    assert s.nodes_changed == 0
    assert s.artifacts_added == 0
    assert s.artifacts_removed == 0
    assert s.artifacts_changed == 0
    assert s.trace_keys_changed == 0
    assert s.context_keys_changed == 0


def test_diff_summary_explicit_values():
    s = DiffSummary(
        nodes_added=2,
        nodes_removed=1,
        nodes_changed=3,
        artifacts_added=4,
        artifacts_removed=0,
        artifacts_changed=2,
        trace_keys_changed=1,
        context_keys_changed=5,
    )
    assert s.nodes_added == 2
    assert s.artifacts_changed == 2
    assert s.context_keys_changed == 5


# ---------------------------------------------------------------------------
# 2. NodeDiff creation
# ---------------------------------------------------------------------------

def test_node_diff_minimal():
    nd = NodeDiff(node_id="n1", change_type=CHANGE_TYPE_MODIFIED)
    assert nd.node_id == "n1"
    assert nd.change_type == CHANGE_TYPE_MODIFIED
    assert nd.left_status is None
    assert nd.right_status is None
    assert nd.artifact_ids_added == []
    assert nd.artifact_ids_removed == []
    assert nd.artifact_ids_changed == []


def test_node_diff_with_statuses():
    nd = NodeDiff(
        node_id="n2",
        change_type=CHANGE_TYPE_MODIFIED,
        left_status="success",
        right_status="failure",
        left_output_ref="run_a/n2/output",
        right_output_ref="run_b/n2/output",
        artifact_ids_added=["art_3"],
        artifact_ids_removed=[],
        artifact_ids_changed=["art_1"],
    )
    assert nd.left_status == "success"
    assert nd.right_status == "failure"
    assert "art_3" in nd.artifact_ids_added
    assert "art_1" in nd.artifact_ids_changed


def test_node_diff_change_type_added():
    nd = NodeDiff(node_id="new_node", change_type=CHANGE_TYPE_ADDED, right_status="success")
    assert nd.change_type == CHANGE_TYPE_ADDED
    assert nd.left_status is None


def test_node_diff_change_type_removed():
    nd = NodeDiff(node_id="old_node", change_type=CHANGE_TYPE_REMOVED, left_status="success")
    assert nd.change_type == CHANGE_TYPE_REMOVED
    assert nd.right_status is None


def test_node_diff_change_type_unchanged():
    nd = NodeDiff(node_id="stable", change_type=CHANGE_TYPE_UNCHANGED)
    assert nd.change_type == CHANGE_TYPE_UNCHANGED


# ---------------------------------------------------------------------------
# 3. ArtifactDiff creation
# ---------------------------------------------------------------------------

def test_artifact_diff_minimal():
    ad = ArtifactDiff(artifact_id="art_1", change_type=CHANGE_TYPE_ADDED)
    assert ad.artifact_id == "art_1"
    assert ad.change_type == CHANGE_TYPE_ADDED
    assert ad.left_hash is None
    assert ad.right_hash is None
    assert ad.left_kind is None
    assert ad.right_kind is None


def test_artifact_diff_with_hashes():
    ad = ArtifactDiff(
        artifact_id="art_2",
        change_type=CHANGE_TYPE_MODIFIED,
        left_hash="abc123",
        right_hash="def456",
        left_kind="provider_output",
        right_kind="provider_output",
    )
    assert ad.left_hash == "abc123"
    assert ad.right_hash == "def456"
    assert ad.left_kind == "provider_output"


def test_artifact_diff_removed():
    ad = ArtifactDiff(
        artifact_id="art_old",
        change_type=CHANGE_TYPE_REMOVED,
        left_hash="dead",
        left_kind="evaluation",
    )
    assert ad.change_type == CHANGE_TYPE_REMOVED
    assert ad.right_hash is None


def test_artifact_diff_unchanged():
    ad = ArtifactDiff(
        artifact_id="art_stable",
        change_type=CHANGE_TYPE_UNCHANGED,
        left_hash="same",
        right_hash="same",
    )
    assert ad.left_hash == ad.right_hash


# ---------------------------------------------------------------------------
# 4. TraceDiff creation
# ---------------------------------------------------------------------------

def test_trace_diff_node_scope():
    td = TraceDiff(
        scope="node",
        key="execution_time_ms",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value=120.5,
        right_value=98.3,
    )
    assert td.scope == "node"
    assert td.key == "execution_time_ms"
    assert td.left_value == 120.5
    assert td.right_value == 98.3


def test_trace_diff_provider_scope():
    td = TraceDiff(
        scope="provider",
        key="tokens_used",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value=100,
        right_value=150,
    )
    assert td.scope == "provider"


def test_trace_diff_plugin_scope():
    td = TraceDiff(
        scope="plugin",
        key="score",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value=0.85,
        right_value=0.92,
    )
    assert td.scope == "plugin"


def test_trace_diff_none_values():
    td = TraceDiff(scope="node", key="status", change_type=CHANGE_TYPE_ADDED)
    assert td.left_value is None
    assert td.right_value is None


# ---------------------------------------------------------------------------
# 5. ContextDiff creation
# ---------------------------------------------------------------------------

def test_context_diff_canonical_key():
    cd = ContextDiff(
        context_key="input.text",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value="hello",
        right_value="world",
    )
    assert cd.context_key == "input.text"
    assert cd.left_value == "hello"
    assert cd.right_value == "world"


def test_context_diff_provider_key():
    cd = ContextDiff(
        context_key="provider.openai.output",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value="response A",
        right_value="response B",
    )
    assert cd.context_key == "provider.openai.output"


def test_context_diff_plugin_key():
    cd = ContextDiff(
        context_key="plugin.rank.score",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value=0.7,
        right_value=0.9,
    )
    assert cd.context_key.startswith("plugin.")


def test_context_diff_added():
    cd = ContextDiff(
        context_key="output.value",
        change_type=CHANGE_TYPE_ADDED,
        right_value="new output",
    )
    assert cd.left_value is None
    assert cd.right_value == "new output"


# ---------------------------------------------------------------------------
# 6. Serialization to dict
# ---------------------------------------------------------------------------

def test_diff_summary_to_dict():
    s = DiffSummary(nodes_added=1, artifacts_changed=2)
    d = s.to_dict()
    assert isinstance(d, dict)
    assert d["nodes_added"] == 1
    assert d["artifacts_changed"] == 2
    assert "context_keys_changed" in d


def test_node_diff_to_dict():
    nd = NodeDiff(node_id="n1", change_type=CHANGE_TYPE_MODIFIED)
    d = nd.to_dict()
    assert isinstance(d, dict)
    assert d["node_id"] == "n1"
    assert d["change_type"] == CHANGE_TYPE_MODIFIED
    assert d["artifact_ids_added"] == []


def test_artifact_diff_to_dict():
    ad = ArtifactDiff(artifact_id="art_1", change_type=CHANGE_TYPE_ADDED, right_hash="abc")
    d = ad.to_dict()
    assert d["artifact_id"] == "art_1"
    assert d["right_hash"] == "abc"
    assert d["left_hash"] is None


def test_trace_diff_to_dict():
    td = TraceDiff(scope="node", key="time", change_type=CHANGE_TYPE_MODIFIED, left_value=1, right_value=2)
    d = td.to_dict()
    assert d["scope"] == "node"
    assert d["left_value"] == 1


def test_context_diff_to_dict():
    cd = ContextDiff(context_key="input.text", change_type=CHANGE_TYPE_MODIFIED, left_value="a")
    d = cd.to_dict()
    assert d["context_key"] == "input.text"
    assert d["left_value"] == "a"


def test_run_diff_to_dict_structure():
    rd = RunDiff(left_run_id="run_a", right_run_id="run_b", status=RUN_DIFF_STATUS_CHANGED)
    d = rd.to_dict()
    assert isinstance(d, dict)
    assert d["left_run_id"] == "run_a"
    assert d["right_run_id"] == "run_b"
    assert d["status"] == RUN_DIFF_STATUS_CHANGED
    assert isinstance(d["node_diffs"], list)
    assert isinstance(d["artifact_diffs"], list)
    assert isinstance(d["trace_diffs"], list)
    assert isinstance(d["context_diffs"], list)
    assert isinstance(d["summary"], dict)


# ---------------------------------------------------------------------------
# 7. JSON compatibility
# ---------------------------------------------------------------------------

def test_diff_summary_json_roundtrip():
    s = DiffSummary(nodes_added=3, artifacts_removed=1)
    j = s.to_json()
    parsed = json.loads(j)
    assert parsed["nodes_added"] == 3
    assert parsed["artifacts_removed"] == 1


def test_node_diff_json_roundtrip():
    nd = NodeDiff(
        node_id="n1",
        change_type=CHANGE_TYPE_MODIFIED,
        left_status="success",
        right_status="failure",
        artifact_ids_added=["art_1"],
    )
    j = nd.to_json()
    parsed = json.loads(j)
    assert parsed["node_id"] == "n1"
    assert parsed["artifact_ids_added"] == ["art_1"]


def test_run_diff_full_json_roundtrip():
    rd = RunDiff(
        left_run_id="run_a",
        right_run_id="run_b",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[NodeDiff(node_id="n1", change_type=CHANGE_TYPE_MODIFIED)],
        artifact_diffs=[ArtifactDiff(artifact_id="art_1", change_type=CHANGE_TYPE_ADDED)],
        context_diffs=[ContextDiff(context_key="input.text", change_type=CHANGE_TYPE_MODIFIED)],
        summary=DiffSummary(nodes_changed=1, artifacts_added=1, context_keys_changed=1),
    )
    j = rd.to_json()
    assert isinstance(j, str)
    parsed = json.loads(j)
    assert parsed["left_run_id"] == "run_a"
    assert len(parsed["node_diffs"]) == 1
    assert parsed["node_diffs"][0]["node_id"] == "n1"
    assert parsed["artifact_diffs"][0]["artifact_id"] == "art_1"
    assert parsed["context_diffs"][0]["context_key"] == "input.text"
    assert parsed["summary"]["nodes_changed"] == 1


def test_json_serializable_with_none_values():
    ad = ArtifactDiff(artifact_id="art_x", change_type=CHANGE_TYPE_ADDED)
    j = ad.to_json()
    parsed = json.loads(j)
    assert parsed["left_hash"] is None
    assert parsed["left_kind"] is None


# ---------------------------------------------------------------------------
# 8. Empty diff scenario
# ---------------------------------------------------------------------------

def test_empty_run_diff():
    rd = RunDiff(
        left_run_id="run_1",
        right_run_id="run_2",
        status=RUN_DIFF_STATUS_IDENTICAL,
    )
    assert rd.node_diffs == []
    assert rd.artifact_diffs == []
    assert rd.trace_diffs == []
    assert rd.context_diffs == []
    assert rd.summary.nodes_added == 0
    assert rd.summary.context_keys_changed == 0


def test_empty_run_diff_is_json_serializable():
    rd = RunDiff(left_run_id="r1", right_run_id="r2", status=RUN_DIFF_STATUS_IDENTICAL)
    j = rd.to_json()
    parsed = json.loads(j)
    assert parsed["node_diffs"] == []
    assert parsed["summary"]["nodes_added"] == 0


# ---------------------------------------------------------------------------
# 9. Modified diff scenario
# ---------------------------------------------------------------------------

def test_modified_diff_scenario():
    """Simulate a run where one node changed output and one artifact was added."""
    nd = NodeDiff(
        node_id="expand_node",
        change_type=CHANGE_TYPE_MODIFIED,
        left_status="success",
        right_status="success",
        left_output_ref="run_a/expand_node/output",
        right_output_ref="run_b/expand_node/output",
        artifact_ids_changed=["art_expand"],
    )
    ad = ArtifactDiff(
        artifact_id="art_new",
        change_type=CHANGE_TYPE_ADDED,
        right_hash="new_hash_abc",
        right_kind="provider_output",
    )
    cd = ContextDiff(
        context_key="provider.openai.output",
        change_type=CHANGE_TYPE_MODIFIED,
        left_value="old response",
        right_value="new response",
    )
    summary = DiffSummary(
        nodes_changed=1,
        artifacts_added=1,
        artifacts_changed=1,
        context_keys_changed=1,
    )
    rd = RunDiff(
        left_run_id="run_a",
        right_run_id="run_b",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[nd],
        artifact_diffs=[ad],
        context_diffs=[cd],
        summary=summary,
    )

    assert rd.status == RUN_DIFF_STATUS_CHANGED
    assert len(rd.node_diffs) == 1
    assert rd.node_diffs[0].change_type == CHANGE_TYPE_MODIFIED
    assert len(rd.artifact_diffs) == 1
    assert rd.artifact_diffs[0].change_type == CHANGE_TYPE_ADDED
    assert rd.context_diffs[0].context_key == "provider.openai.output"
    assert rd.summary.nodes_changed == 1
    assert rd.summary.artifacts_added == 1

    d = rd.to_dict()
    assert d["status"] == RUN_DIFF_STATUS_CHANGED
    assert d["summary"]["context_keys_changed"] == 1


def test_incomplete_run_diff_scenario():
    rd = RunDiff(
        left_run_id="run_ok",
        right_run_id="run_failed",
        status=RUN_DIFF_STATUS_INCOMPLETE,
        node_diffs=[
            NodeDiff(node_id="n1", change_type=CHANGE_TYPE_UNCHANGED, left_status="success"),
            NodeDiff(node_id="n2", change_type=CHANGE_TYPE_MODIFIED, left_status="success", right_status="failure"),
        ],
    )
    assert rd.status == RUN_DIFF_STATUS_INCOMPLETE
    assert len(rd.node_diffs) == 2


# ---------------------------------------------------------------------------
# Constants correctness
# ---------------------------------------------------------------------------

def test_valid_run_diff_statuses_constant():
    assert RUN_DIFF_STATUS_IDENTICAL in VALID_RUN_DIFF_STATUSES
    assert RUN_DIFF_STATUS_CHANGED in VALID_RUN_DIFF_STATUSES
    assert RUN_DIFF_STATUS_INCOMPLETE in VALID_RUN_DIFF_STATUSES
    assert len(VALID_RUN_DIFF_STATUSES) == 3


def test_valid_change_types_constant():
    assert CHANGE_TYPE_ADDED in VALID_CHANGE_TYPES
    assert CHANGE_TYPE_REMOVED in VALID_CHANGE_TYPES
    assert CHANGE_TYPE_MODIFIED in VALID_CHANGE_TYPES
    assert CHANGE_TYPE_UNCHANGED in VALID_CHANGE_TYPES
    assert len(VALID_CHANGE_TYPES) == 4
