
"""
T1: Engine Trace Minimum Contract

Purpose:
- Before migrating legacy runner/state invariants, we freeze the minimum trace contract
  of Engine.execute() and its returned ExecutionTrace.
"""

from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.trace import ExecutionTrace


def _make_min_engine() -> Engine:
    # Minimal 2-node graph: n1 -> n2
    return Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )


def test_execute_returns_execution_trace_and_sets_core_fields():
    eng = _make_min_engine()
    trace = eng.execute(revision_id="r1")

    assert isinstance(trace, ExecutionTrace)

    # Required identity fields
    assert trace.execution_id
    assert trace.revision_id == "r1"
    assert trace.structural_fingerprint

    # Timing evidence should be present
    assert trace.started_at is not None
    assert trace.finished_at is not None
    assert trace.duration_ms is not None
    assert trace.duration_ms >= 0

    # Coverage: every expected node id must exist in nodes mapping
    assert list(trace.expected_node_ids) == ["n1", "n2"]
    assert set(trace.nodes.keys()) == {"n1", "n2"}


def test_structural_fingerprint_is_stable_for_same_structure():
    eng1 = _make_min_engine()
    eng2 = _make_min_engine()

    t1 = eng1.execute(revision_id="r1")
    t2 = eng2.execute(revision_id="r2")

    # Structural fingerprint should depend on graph structure, not revision_id
    assert t1.structural_fingerprint == t2.structural_fingerprint
