from __future__ import annotations

"""T1: Engine Determinism Contract

Invariant:
Given the same graph structure, the per-node structural outcomes must be identical
across repeated executions, even if execution_id/revision_id/time fields differ.

We intentionally assert on *structural* fields only:
- node_status
- stage statuses (pre/core/post)
- reason_code

We do NOT assert on timestamps or execution_id.
"""

from src.engine.engine import Engine
from src.engine.model import Channel


def _make_min_engine() -> Engine:
    # Minimal 2-node graph: n1 -> n2
    return Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )


def _signature(trace) -> tuple:
    # Structural fingerprint should be stable for identical graphs.
    fp = trace.structural_fingerprint

    node_items = []
    for nid in sorted(trace.nodes.keys()):
        nt = trace.nodes[nid]
        node_items.append(
            (
                nid,
                nt.node_status,
                nt.pre_status,
                nt.core_status,
                nt.post_status,
                nt.reason_code,
            )
        )
    return (fp, tuple(node_items))


def test_engine_determinism_structural_signature_50_runs():
    sigs = []
    for i in range(50):
        eng = _make_min_engine()
        trace = eng.execute(revision_id=f"r{i}")
        sigs.append(_signature(trace))

    first = sigs[0]
    for s in sigs[1:]:
        assert s == first
