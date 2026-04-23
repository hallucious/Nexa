from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel, FlowRule
from src.engine.types import FlowPolicy, NodeStatus


def test_node_handler_runs_and_records_output_snapshot():
    def h1(_inp):
        return {"a": 1}

    def h2(inp):
        # input is namespaced by parent node_id
        assert inp["n1"]["a"] == 1
        return {"b": 2}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={"n1": h1, "n2": h2},
    )

    trace = eng.execute(revision_id="r1")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n1"].output_snapshot == {"a": 1}
    assert trace.nodes["n2"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].input_snapshot == {"n1": {"a": 1}}
    assert trace.nodes["n2"].output_snapshot == {"b": 2}


def test_handler_exception_marks_failure_and_skips_downstream():
    def boom(_inp):
        raise RuntimeError("boom")

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={"n1": boom},
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED


def test_any_success_still_executes_handler_when_condition_met():
    def h1(_):
        return {"ok": True}

    def h2(_):
        return {}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n3"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n3"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n3"),
        ],
        flow=[FlowRule(rule_id="fr1", node_id="n3", policy=FlowPolicy.ANY_SUCCESS)],
        handlers={"n1": h1, "n3": h2},
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    # n2 is NOT_REACHED, but ANY_SUCCESS should allow n3 to run
    assert trace.nodes["n2"].node_status == NodeStatus.NOT_REACHED
    assert trace.nodes["n3"].node_status == NodeStatus.SUCCESS
