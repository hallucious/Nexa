"""
tests/test_execution_diff_engine.py

Tests for the Execution Diff Engine (Step181).

Covers:
 1. identical runs → empty diff / status=identical
 2. node added
 3. node removed
 4. node artifact change
 5. dependency change
 6. metadata change
 7. multiple node changes
 8. artifact additions (top-level)
 9. artifact removals (top-level)
10. artifact modifications (top-level)
11. context key changes
12. error cases (bad input types)
"""
from __future__ import annotations

import pytest

from src.engine.execution_diff_engine import compare_runs
from src.engine.execution_diff_model import (
    CHANGE_TYPE_ADDED,
    CHANGE_TYPE_MODIFIED,
    CHANGE_TYPE_REMOVED,
    RUN_DIFF_STATUS_CHANGED,
    RUN_DIFF_STATUS_IDENTICAL,
    RunDiff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(run_id: str, nodes: dict = None, artifacts: dict = None, context: dict = None) -> dict:
    """Build a minimal run snapshot dict."""
    r: dict = {"run_id": run_id}
    if nodes is not None:
        r["nodes"] = nodes
    if artifacts is not None:
        r["artifacts"] = artifacts
    if context is not None:
        r["context"] = context
    return r


def _node(status="success", output=None, output_ref=None, artifacts=None, dependencies=None, metadata=None) -> dict:
    n: dict = {}
    if status is not None:
        n["status"] = status
    if output is not None:
        n["output"] = output
    if output_ref is not None:
        n["output_ref"] = output_ref
    if artifacts is not None:
        n["artifacts"] = artifacts
    if dependencies is not None:
        n["dependencies"] = dependencies
    if metadata is not None:
        n["metadata"] = metadata
    return n


def _art(hash_val: str = "hash_abc", kind: str = "provider_output") -> dict:
    return {"hash": hash_val, "kind": kind}


# ---------------------------------------------------------------------------
# 1. Identical runs → status=identical, empty diffs
# ---------------------------------------------------------------------------

def test_identical_empty_runs():
    left = _run("r1")
    right = _run("r1")
    diff = compare_runs(left, right)
    assert isinstance(diff, RunDiff)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL
    assert diff.node_diffs == []
    assert diff.artifact_diffs == []
    assert diff.context_diffs == []
    assert diff.summary.nodes_added == 0
    assert diff.summary.nodes_removed == 0
    assert diff.summary.nodes_changed == 0


def test_identical_runs_with_same_nodes():
    nodes = {
        "n1": _node(status="success", output="hello"),
        "n2": _node(status="success", output="world"),
    }
    left = _run("r1", nodes=nodes)
    right = _run("r2", nodes=nodes)
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL
    assert diff.node_diffs == []


def test_run_ids_are_captured():
    left = _run("run_alpha")
    right = _run("run_beta")
    diff = compare_runs(left, right)
    assert diff.left_run_id == "run_alpha"
    assert diff.right_run_id == "run_beta"


# ---------------------------------------------------------------------------
# 2. Node added
# ---------------------------------------------------------------------------

def test_node_added():
    left = _run("r1", nodes={"n1": _node()})
    right = _run("r2", nodes={"n1": _node(), "n2": _node(status="success")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    added = [nd for nd in diff.node_diffs if nd.change_type == CHANGE_TYPE_ADDED]
    assert len(added) == 1
    assert added[0].node_id == "n2"
    assert diff.summary.nodes_added == 1


def test_node_added_carries_status():
    left = _run("r1", nodes={})
    right = _run("r2", nodes={"n_new": _node(status="success", output_ref="r2/n_new/out")})
    diff = compare_runs(left, right)
    nd = diff.node_diffs[0]
    assert nd.right_status == "success"
    assert nd.right_output_ref == "r2/n_new/out"
    assert nd.left_status is None


# ---------------------------------------------------------------------------
# 3. Node removed
# ---------------------------------------------------------------------------

def test_node_removed():
    left = _run("r1", nodes={"n1": _node(), "n2": _node()})
    right = _run("r2", nodes={"n1": _node()})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    removed = [nd for nd in diff.node_diffs if nd.change_type == CHANGE_TYPE_REMOVED]
    assert len(removed) == 1
    assert removed[0].node_id == "n2"
    assert diff.summary.nodes_removed == 1


def test_node_removed_carries_left_status():
    left = _run("r1", nodes={"gone": _node(status="failure")})
    right = _run("r2", nodes={})
    diff = compare_runs(left, right)
    nd = diff.node_diffs[0]
    assert nd.change_type == CHANGE_TYPE_REMOVED
    assert nd.left_status == "failure"
    assert nd.right_status is None


# ---------------------------------------------------------------------------
# 4. Node artifact change
# ---------------------------------------------------------------------------

def test_node_artifact_added():
    left_node = _node(artifacts={})
    right_node = _node(artifacts={"art_new": _art("h1")})
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    nd = diff.node_diffs[0]
    assert nd.change_type == CHANGE_TYPE_MODIFIED
    assert "art_new" in nd.artifact_ids_added
    assert diff.summary.nodes_changed == 1


def test_node_artifact_removed():
    left_node = _node(artifacts={"art_old": _art("h1")})
    right_node = _node(artifacts={})
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    nd = diff.node_diffs[0]
    assert "art_old" in nd.artifact_ids_removed


def test_node_artifact_hash_changed():
    left_node = _node(artifacts={"art_1": _art("hash_old")})
    right_node = _node(artifacts={"art_1": _art("hash_new")})
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    nd = diff.node_diffs[0]
    assert "art_1" in nd.artifact_ids_changed


# ---------------------------------------------------------------------------
# 5. Dependency change
# ---------------------------------------------------------------------------

def test_dependency_change_detected():
    left_node = _node(dependencies=["n0"])
    right_node = _node(dependencies=["n0", "n_extra"])
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    nd = diff.node_diffs[0]
    assert nd.change_type == CHANGE_TYPE_MODIFIED


def test_dependency_order_does_not_matter():
    """Same deps in different order → no change."""
    left_node = _node(dependencies=["a", "b", "c"])
    right_node = _node(dependencies=["c", "a", "b"])
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL


# ---------------------------------------------------------------------------
# 6. Metadata change
# ---------------------------------------------------------------------------

def test_metadata_change_detected():
    left_node = _node(metadata={"version": "1"})
    right_node = _node(metadata={"version": "2"})
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    nd = diff.node_diffs[0]
    assert nd.change_type == CHANGE_TYPE_MODIFIED


def test_metadata_same_no_change():
    left_node = _node(metadata={"key": "value"})
    right_node = _node(metadata={"key": "value"})
    left = _run("r1", nodes={"n1": left_node})
    right = _run("r2", nodes={"n1": right_node})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL


# ---------------------------------------------------------------------------
# 7. Multiple node changes
# ---------------------------------------------------------------------------

def test_multiple_node_changes():
    left = _run("r1", nodes={
        "n1": _node(status="success"),
        "n2": _node(status="success"),
        "n3": _node(status="success"),
    })
    right = _run("r2", nodes={
        "n1": _node(status="failure"),  # modified (status)
        "n2": _node(status="success"),  # unchanged
        "n4": _node(status="success"),  # added (n3 removed → n4)
    })
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    assert diff.summary.nodes_added == 1
    assert diff.summary.nodes_removed == 1
    assert diff.summary.nodes_changed == 1
    assert len(diff.node_diffs) == 3  # added n4 + removed n3 + modified n1


def test_multiple_nodes_all_unchanged():
    nodes = {
        "n1": _node(status="success", output="a"),
        "n2": _node(status="success", output="b"),
        "n3": _node(status="success", output="c"),
    }
    left = _run("r1", nodes=nodes)
    right = _run("r2", nodes=nodes)
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL
    assert diff.node_diffs == []


# ---------------------------------------------------------------------------
# 8. Top-level artifact additions
# ---------------------------------------------------------------------------

def test_top_level_artifact_added():
    left = _run("r1", artifacts={})
    right = _run("r2", artifacts={"art_1": _art("h1")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    assert len(diff.artifact_diffs) == 1
    assert diff.artifact_diffs[0].change_type == CHANGE_TYPE_ADDED
    assert diff.artifact_diffs[0].artifact_id == "art_1"
    assert diff.summary.artifacts_added == 1


def test_top_level_multiple_artifacts_added():
    left = _run("r1", artifacts={})
    right = _run("r2", artifacts={
        "art_a": _art("ha"),
        "art_b": _art("hb"),
    })
    diff = compare_runs(left, right)
    assert diff.summary.artifacts_added == 2
    assert diff.summary.artifacts_removed == 0


# ---------------------------------------------------------------------------
# 9. Top-level artifact removals
# ---------------------------------------------------------------------------

def test_top_level_artifact_removed():
    left = _run("r1", artifacts={"art_old": _art("h1")})
    right = _run("r2", artifacts={})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    assert diff.artifact_diffs[0].change_type == CHANGE_TYPE_REMOVED
    assert diff.artifact_diffs[0].left_hash == "h1"
    assert diff.summary.artifacts_removed == 1


# ---------------------------------------------------------------------------
# 10. Top-level artifact modifications
# ---------------------------------------------------------------------------

def test_top_level_artifact_hash_changed():
    left = _run("r1", artifacts={"art_1": _art("old_hash")})
    right = _run("r2", artifacts={"art_1": _art("new_hash")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    ad = diff.artifact_diffs[0]
    assert ad.change_type == CHANGE_TYPE_MODIFIED
    assert ad.left_hash == "old_hash"
    assert ad.right_hash == "new_hash"
    assert diff.summary.artifacts_changed == 1


def test_top_level_artifact_kind_changed():
    left = _run("r1", artifacts={"art_1": {"hash": "h1", "kind": "text"}})
    right = _run("r2", artifacts={"art_1": {"hash": "h1", "kind": "json"}})
    diff = compare_runs(left, right)
    assert diff.artifact_diffs[0].change_type == CHANGE_TYPE_MODIFIED


def test_top_level_artifact_unchanged():
    left = _run("r1", artifacts={"art_1": _art("same_hash", "provider_output")})
    right = _run("r2", artifacts={"art_1": _art("same_hash", "provider_output")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL
    assert diff.artifact_diffs == []


# ---------------------------------------------------------------------------
# 11. Context key changes
# ---------------------------------------------------------------------------

def test_context_key_added():
    left = _run("r1", context={})
    right = _run("r2", context={"input.text.value": "hello"})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    assert len(diff.context_diffs) == 1
    cd = diff.context_diffs[0]
    assert cd.context_key == "input.text.value"
    assert cd.change_type == CHANGE_TYPE_ADDED
    assert cd.right_value == "hello"
    assert diff.summary.context_keys_changed == 1


def test_context_key_removed():
    left = _run("r1", context={"provider.openai.output": "old"})
    right = _run("r2", context={})
    diff = compare_runs(left, right)
    cd = diff.context_diffs[0]
    assert cd.change_type == CHANGE_TYPE_REMOVED
    assert cd.left_value == "old"


def test_context_key_modified():
    left = _run("r1", context={"output.summary.value": "v1"})
    right = _run("r2", context={"output.summary.value": "v2"})
    diff = compare_runs(left, right)
    cd = diff.context_diffs[0]
    assert cd.change_type == CHANGE_TYPE_MODIFIED
    assert cd.left_value == "v1"
    assert cd.right_value == "v2"


def test_context_unchanged():
    ctx = {"input.text.value": "same", "plugin.rank.score": 0.9}
    diff = compare_runs(_run("r1", context=ctx), _run("r2", context=ctx))
    assert diff.context_diffs == []


# ---------------------------------------------------------------------------
# 12. Error cases
# ---------------------------------------------------------------------------

def test_non_dict_left_raises():
    with pytest.raises(TypeError):
        compare_runs("not_a_dict", _run("r2"))


def test_non_dict_right_raises():
    with pytest.raises(TypeError):
        compare_runs(_run("r1"), 42)


# ---------------------------------------------------------------------------
# 13. Edge cases / determinism
# ---------------------------------------------------------------------------

def test_empty_runs_are_identical():
    diff = compare_runs({}, {})
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL


def test_result_is_run_diff_instance():
    diff = compare_runs(_run("a"), _run("b"))
    assert isinstance(diff, RunDiff)


def test_diff_is_serializable_to_dict():
    left = _run("r1", nodes={"n1": _node(status="success")})
    right = _run("r2", nodes={"n1": _node(status="failure")})
    diff = compare_runs(left, right)
    d = diff.to_dict()
    assert isinstance(d, dict)
    assert d["status"] == RUN_DIFF_STATUS_CHANGED


def test_diff_is_json_serializable():
    import json
    left = _run("r1", nodes={"n1": _node()}, artifacts={"a1": _art("h1")})
    right = _run("r2", nodes={"n1": _node(status="failure")}, artifacts={"a1": _art("h2")})
    diff = compare_runs(left, right)
    j = diff.to_json()
    parsed = json.loads(j)
    assert parsed["left_run_id"] == "r1"


def test_compare_runs_is_deterministic():
    """Same inputs always produce same output."""
    left = _run("r1", nodes={"n1": _node(output="x"), "n2": _node(output="y")})
    right = _run("r2", nodes={"n1": _node(output="z"), "n3": _node()})
    diff1 = compare_runs(left, right)
    diff2 = compare_runs(left, right)
    assert diff1.to_dict() == diff2.to_dict()


def test_node_status_change_is_detected():
    left = _run("r1", nodes={"n1": _node(status="success")})
    right = _run("r2", nodes={"n1": _node(status="failure")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    nd = diff.node_diffs[0]
    assert nd.left_status == "success"
    assert nd.right_status == "failure"


def test_missing_nodes_key_treated_as_empty():
    """Runs without 'nodes' key should be treated as zero nodes."""
    left = {}
    right = {"nodes": {"n1": _node()}}
    diff = compare_runs(left, right)
    assert diff.summary.nodes_added == 1


# ---------------------------------------------------------------------------
# Step181.1 — output_ref change detection
# ---------------------------------------------------------------------------

def test_output_ref_changed_produces_node_diff():
    """output_ref change alone must trigger CHANGE_TYPE_MODIFIED."""
    left = _run("r1", nodes={"n1": _node(output_ref="r1/n1/out")})
    right = _run("r2", nodes={"n1": _node(output_ref="r2/n1/out")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_CHANGED
    assert len(diff.node_diffs) == 1
    nd = diff.node_diffs[0]
    assert nd.change_type == CHANGE_TYPE_MODIFIED
    assert nd.left_output_ref == "r1/n1/out"
    assert nd.right_output_ref == "r2/n1/out"


def test_output_ref_same_no_diff_when_other_fields_same():
    """Identical output_ref with all other fields identical → no node diff."""
    left = _run("r1", nodes={"n1": _node(status="success", output_ref="runs/n1/out")})
    right = _run("r2", nodes={"n1": _node(status="success", output_ref="runs/n1/out")})
    diff = compare_runs(left, right)
    assert diff.status == RUN_DIFF_STATUS_IDENTICAL
    assert diff.node_diffs == []


def test_output_ref_change_counted_in_summary():
    """summary.nodes_changed must reflect an output_ref-only change."""
    left = _run("r1", nodes={
        "n1": _node(output_ref="r1/n1"),
        "n2": _node(output_ref="r1/n2"),
    })
    right = _run("r2", nodes={
        "n1": _node(output_ref="r2/n1"),   # changed
        "n2": _node(output_ref="r1/n2"),   # unchanged
    })
    diff = compare_runs(left, right)
    assert diff.summary.nodes_changed == 1
    assert diff.summary.nodes_added == 0
    assert diff.summary.nodes_removed == 0


def test_output_context_change_promotes_node_change():
    left = _run(
        "r1",
        context={"output.planner_node": {"text": "old"}},
    )
    right = _run(
        "r2",
        context={"output.planner_node": {"text": "new"}},
    )

    diff = compare_runs(left, right)

    assert diff.status == RUN_DIFF_STATUS_CHANGED
    assert diff.summary.nodes_changed == 1
    assert any(nd.node_id == "planner_node" and nd.change_type == CHANGE_TYPE_MODIFIED for nd in diff.node_diffs)


def test_output_context_change_deduplicates_multiple_keys_for_same_node():
    left = _run(
        "r1",
        context={
            "output.planner_node": {"text": "old"},
            "output.planner_node.text": "old",
        },
    )
    right = _run(
        "r2",
        context={
            "output.planner_node": {"text": "new"},
            "output.planner_node.text": "new",
        },
    )

    diff = compare_runs(left, right)

    planner_diffs = [nd for nd in diff.node_diffs if nd.node_id == "planner_node"]
    assert len(planner_diffs) == 1
    assert diff.summary.nodes_changed == 1


def test_output_context_change_ignores_non_node_output_namespace_key():
    left = _run("r1", context={"output.output": "Alpha"})
    right = _run("r2", context={"output.output": "Beta"})

    diff = compare_runs(left, right)

    assert diff.summary.nodes_changed == 0
    assert diff.node_diffs == []
