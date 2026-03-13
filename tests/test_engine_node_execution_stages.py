from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel, FlowRule
from src.engine.types import FlowPolicy, NodeStatus, StageStatus


def test_stages_pre_failure_skips_core_but_runs_post_and_fails_node():
    def pre(_inp):
        raise RuntimeError("bad input")

    core_ran = {"v": False}

    def core(_inp):
        core_ran["v"] = True
        return {"x": 1}

    def post(ctx):
        # Post must still run even if pre/core failed
        assert ctx["pre_status"] == StageStatus.FAILURE.value
        return {"post": True}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": {"pre": pre, "core": core, "post": post}},
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].pre_status == StageStatus.FAILURE
    assert trace.nodes["n1"].core_status == StageStatus.SKIPPED
    assert trace.nodes["n1"].post_status == StageStatus.SUCCESS
    assert core_ran["v"] is False


def test_stages_post_can_override_output_snapshot():
    def core(_inp):
        return {"core": 1}

    def post(ctx):
        assert ctx["core_output"] == {"core": 1}
        return {"final": 2}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": {"core": core, "post": post}},
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n1"].output_snapshot == {"final": 2}


def test_flowpolicy_any_success_still_gates_execution_with_staged_handlers():
    def h1(_):
        return {"ok": True}

    def pre(inp):
        # passthrough / normalize
        return dict(inp)

    def core(inp):
        # n1 output is namespaced
        assert inp["n1"]["ok"] is True
        return {"ran": True}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n3"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n3"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n3"),
        ],
        flow=[FlowRule(rule_id="fr1", node_id="n3", policy=FlowPolicy.ANY_SUCCESS)],
        handlers={
            "n1": h1,
            "n3": {"pre": pre, "core": core},
        },
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.NOT_REACHED
    assert trace.nodes["n3"].node_status == NodeStatus.SUCCESS
