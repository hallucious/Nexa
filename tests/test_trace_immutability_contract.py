from __future__ import annotations

"""Step48: Trace Immutability Contract

Invariant:
After engine.execute() completes,
the returned trace object must be immutable from external mutation.

We test:
- Direct attribute reassignment blocked
- Node-level status mutation blocked
"""

import pytest
from src.engine.engine import Engine
from src.engine.model import Channel


def _make_min_engine() -> Engine:
    return Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )


def test_trace_object_immutable_after_execution():
    eng = _make_min_engine()
    trace = eng.execute(revision_id="r1")

    # Attempt to mutate top-level attribute
    with pytest.raises(Exception):
        trace.structural_fingerprint = "tampered"

    # Attempt to mutate node-level state
    nid = sorted(trace.nodes.keys())[0]
    node_trace = trace.nodes[nid]

    with pytest.raises(Exception):
        node_trace.node_status = "TAMPERED"
