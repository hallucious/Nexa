from __future__ import annotations

"""Step50: Trace Serialization Stability Contract

Invariant:
- ExecutionTrace must provide a stable JSON serialization API.
- Repeated serialization without mutation must produce identical JSON.
"""

from src.engine.engine import Engine
from src.engine.model import Channel


def _make_engine() -> Engine:
    return Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )


def test_trace_json_serialization_stable():
    eng = _make_engine()
    trace = eng.execute(revision_id="r-serialize")

    j1 = trace.to_json(stable=True, ensure_ascii=False)
    j2 = trace.to_json(stable=True, ensure_ascii=False)

    assert j1 == j2
