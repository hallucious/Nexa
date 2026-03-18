
"""
T1: Engine Repeatability Contract

Purpose:
Replace legacy runner repeatability invariant with Engine-level invariant.

Invariant:
For identical graph structure and inputs, terminal node statuses
must be structurally identical across repeated executions.
"""

from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.types import NodeStatus


def _make_min_engine() -> Engine:
    return Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )


def test_engine_repeatability_same_structure_50_runs():
    results = []

    for i in range(50):
        eng = _make_min_engine()
        trace = eng.execute(revision_id=f"r{i}")
        terminal_tuple = tuple(
            (nid, trace.nodes[nid].node_status)
            for nid in sorted(trace.nodes.keys())
        )
        results.append(terminal_tuple)

    # All runs must produce identical structural outcomes
    first = results[0]
    for r in results[1:]:
        assert r == first
