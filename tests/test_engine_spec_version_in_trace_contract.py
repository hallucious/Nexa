from __future__ import annotations

"""Step49: Engine embeds spec versions into ExecutionTrace.meta

Invariant:
- Engine execution must stamp the active spec versions used by the runtime into trace.meta.
- This strengthens the spec-version sync contract at the execution artifact level.
"""

from src.engine.engine import ENGINE_EXECUTION_MODEL_VERSION, ENGINE_TRACE_MODEL_VERSION
from src.engine.engine import Engine
from src.engine.model import Channel


def test_engine_trace_meta_includes_spec_versions():
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )
    trace = eng.execute(revision_id="r-spec")

    assert trace.meta is not None
    sv = trace.meta.get("spec_versions")
    assert isinstance(sv, dict)

    assert sv.get("execution_model") == ENGINE_EXECUTION_MODEL_VERSION
    assert sv.get("trace_model") == ENGINE_TRACE_MODEL_VERSION
