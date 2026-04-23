"""
test_node_fallback_recovery.py

Contract tests for node_fallback_map (Node Recovery / Fallback Strategy v1).
"""
from __future__ import annotations

import pytest

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.types import NodeStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fail(inp):
    raise RuntimeError("forced failure")


def _ok(inp):
    return {"result": "ok"}


def _ok_b(inp):
    return {"result": "fallback_ok"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fallback success replaces failure
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_success_replaces_failure():
    """When primary fails and fallback succeeds, node ends up SUCCESS."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _ok_b},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_fb_ok")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n1"].output_snapshot == {"result": "fallback_ok"}


def test_fallback_success_node_id_preserved():
    """After fallback recovery the trace still uses the original node_id."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _ok},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_id")

    # node_id in trace.nodes must be the original, not the fallback
    assert "n1" in trace.nodes
    assert trace.nodes["n1"].node_id == "n1"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fallback absent → original failure preserved
# ─────────────────────────────────────────────────────────────────────────────

def test_no_fallback_preserves_original_failure():
    """Without a fallback entry, a failed node remains FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _fail},
    )
    trace = eng.execute(revision_id="r_no_fb")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE


def test_empty_fallback_map_preserves_behavior():
    """Providing an empty node_fallback_map has no effect."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _fail},
        node_fallback_map={},
    )
    trace = eng.execute(revision_id="r_empty_map")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fallback failure → still failure
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_failure_keeps_failure():
    """If fallback also fails, the node is still FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _fail},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_fb_fail")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].output_snapshot is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Downstream sees SUCCESS after recovery
# ─────────────────────────────────────────────────────────────────────────────

def test_downstream_sees_success_after_recovery():
    """After fallback recovery, downstream nodes see the node as SUCCESS."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={"n1": _fail, "n1_backup": _ok, "n2": _ok},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_downstream_ok")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.SUCCESS


def test_downstream_skipped_when_fallback_also_fails():
    """If both primary and fallback fail, downstream is still SKIPPED (STRICT)."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={"n1": _fail, "n1_backup": _fail, "n2": _ok},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_downstream_skip")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fallback executed only once
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_executed_only_once():
    """The fallback handler is called at most once per primary failure."""
    call_log = []

    def counting_fallback(inp):
        call_log.append("called")
        return {"r": "ok"}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": counting_fallback},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_once")

    assert len(call_log) == 1, "fallback must be called exactly once"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Recovery metadata recorded correctly
# ─────────────────────────────────────────────────────────────────────────────

def test_recovery_meta_present_on_fallback_success():
    """When fallback succeeds, node.meta must include recovery block."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _ok},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_meta_ok")

    meta = trace.nodes["n1"].meta
    assert meta is not None
    assert "recovery" in meta
    rec = meta["recovery"]
    assert rec["used"] is True
    assert rec["fallback_node"] == "n1_backup"
    assert "original_failure" in rec
    assert isinstance(rec["original_failure"], dict)


def test_recovery_meta_present_on_fallback_failure():
    """When fallback also fails, node.meta must include recovery block."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _fail},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_meta_fail")

    meta = trace.nodes["n1"].meta
    assert meta is not None
    assert "recovery" in meta
    rec = meta["recovery"]
    assert rec["used"] is True
    assert rec["fallback_node"] == "n1_backup"
    assert "original_failure" in rec
    assert "fallback_failure" in rec


def test_no_recovery_meta_when_fallback_not_used():
    """When there is no fallback or node succeeds, no recovery block in meta."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _ok},
    )
    trace = eng.execute(revision_id="r_no_recovery_meta")

    meta = trace.nodes["n1"].meta
    if meta is not None:
        assert "recovery" not in meta


# ─────────────────────────────────────────────────────────────────────────────
# 7. No effect when fallback_map empty
# ─────────────────────────────────────────────────────────────────────────────

def test_success_path_unaffected_by_fallback_map():
    """Existing successful execution is unaffected by adding a fallback_map."""
    handlers_ok = {"n1": _ok, "n2": _ok}

    eng_no_map = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers=handlers_ok,
    )
    eng_with_map = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers=handlers_ok,
        node_fallback_map={},
    )

    t1 = eng_no_map.execute(revision_id="r_no_map")
    t2 = eng_with_map.execute(revision_id="r_with_empty_map")

    assert t1.nodes["n1"].node_status == t2.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert t1.nodes["n2"].node_status == t2.nodes["n2"].node_status == NodeStatus.SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# 8. Fallback node not in graph → handled safely
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_node_not_in_node_ids_results_in_failure():
    """A fallback_node_id not registered in node_ids is a config error → FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _fail},
        node_fallback_map={"n1": "nonexistent_node"},
    )
    trace = eng.execute(revision_id="r_unknown_fallback")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].reason_code == "ENG-FALLBACK-UNKNOWN-NODE"


def test_fallback_self_reference_is_config_error():
    """fallback_node_id == primary node_id is a config error → FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _fail},
        node_fallback_map={"n1": "n1"},
    )
    trace = eng.execute(revision_id="r_self_ref")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].reason_code == "ENG-FALLBACK-SELF-REF"


def test_fallback_missing_handler_uses_noop():
    """A fallback node with no registered handler uses the noop (returns {}) → SUCCESS."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail},  # n1_backup has no handler → noop
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_noop_fallback")

    # noop handler succeeds with empty output
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# Engine-level invariants preserved
# ─────────────────────────────────────────────────────────────────────────────

def test_engine_validation_lifecycle_unaffected_by_fallback():
    """Fallback does not affect engine-level validation or trace.meta keys."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _ok},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_lifecycle")

    assert "validation" in trace.meta
    assert "pre_validation" in trace.meta
    assert "post_validation" in trace.meta
    assert "decision" in trace.meta
    assert trace.validation_success is True


def test_fallback_input_snapshot_matches_primary():
    """Fallback receives the same input_snapshot as the primary node."""
    received = {}

    def capture_fallback(inp):
        received.update(inp)
        return {"captured": True}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n2_backup"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={
            "n1": lambda inp: {"sentinel": 42},
            "n2": _fail,
            "n2_backup": capture_fallback,
        },
        node_fallback_map={"n2": "n2_backup"},
    )
    trace = eng.execute(revision_id="r_input_match")

    # n2's input is merged from n1's output = {"n1": {"sentinel": 42}}
    assert "n1" in received
    assert received["n1"]["sentinel"] == 42
