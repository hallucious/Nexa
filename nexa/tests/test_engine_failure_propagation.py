from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel, FlowPolicy, FlowRule
from src.engine.types import NodeStatus


def test_any_success_allows_downstream_when_one_parent_fails_but_another_succeeds():
    # Graph:
    # e -> a
    # e -> b
    # a -> c
    # b -> c
    def e(_):
        return {}

    def a(_):
        raise RuntimeError("boom")

    def b(_):
        return {"ok": True}

    def c(inp):
        # input is namespaced by parent node_id
        assert inp["b"]["ok"] is True
        return {"done": True}

    eng = Engine(
        entry_node_id="e",
        node_ids=["e", "a", "b", "c"],
        channels=[
            Channel(channel_id="c_e_a", src_node_id="e", dst_node_id="a"),
            Channel(channel_id="c_e_b", src_node_id="e", dst_node_id="b"),
            Channel(channel_id="c_a_c", src_node_id="a", dst_node_id="c"),
            Channel(channel_id="c_b_c", src_node_id="b", dst_node_id="c"),
        ],
        flow=[FlowRule(rule_id="fr_c", node_id="c", policy=FlowPolicy.ANY_SUCCESS)],
        handlers={"e": e, "a": a, "b": b, "c": c},
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["a"].node_status == NodeStatus.FAILURE
    assert trace.nodes["b"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["c"].node_status == NodeStatus.SUCCESS


def test_all_success_skips_downstream_when_any_parent_fails():
    # Same graph as above; policy defaults to ALL_SUCCESS.
    def e(_):
        return {}

    def a(_):
        raise RuntimeError("boom")

    def b(_):
        return {"ok": True}

    def c(_):
        raise AssertionError("c must not run under ALL_SUCCESS when a fails")

    eng = Engine(
        entry_node_id="e",
        node_ids=["e", "a", "b", "c"],
        channels=[
            Channel(channel_id="c_e_a", src_node_id="e", dst_node_id="a"),
            Channel(channel_id="c_e_b", src_node_id="e", dst_node_id="b"),
            Channel(channel_id="c_a_c", src_node_id="a", dst_node_id="c"),
            Channel(channel_id="c_b_c", src_node_id="b", dst_node_id="c"),
        ],
        handlers={"e": e, "a": a, "b": b, "c": c},
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["a"].node_status == NodeStatus.FAILURE
    assert trace.nodes["b"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["c"].node_status == NodeStatus.SKIPPED
