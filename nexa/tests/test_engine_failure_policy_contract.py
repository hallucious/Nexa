
"""
T1: Engine Failure Propagation Contract

Purpose:
Freeze minimal failure → skip propagation semantics at Engine level
before removing legacy runner policy tests.

Invariant (v1 semantics):
If upstream node fails, downstream nodes must become SKIPPED.
"""

from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.types import NodeStatus, StageStatus
from src.engine.types import StageResult


def _failing_handler(**kwargs):
    # core stage fails
    return StageResult(status=StageStatus.FAILURE, reason_code="TEST_FAIL")


def test_upstream_failure_causes_downstream_skipped():
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={
            "n1": {"core": _failing_handler}
        },
    )

    trace = eng.execute(revision_id="r_fail")

    # n1 must fail
    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE

    # downstream must be skipped (v1 propagation semantics)
    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED
