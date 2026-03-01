from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel, FlowRule
from src.engine.types import FlowPolicy
from src.engine.types import NodeStatus


def test_all_success_propagation_linear():
    # n1 -> n2 -> n3
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n3"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n3"),
        ],
    )

    trace = eng.execute(revision_id="r1")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n3"].node_status == NodeStatus.SUCCESS


def test_all_success_multi_parent():
    # n1 -> n3
    # n2 -> n3
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n3"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n3"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n3"),
        ],
    )

    # n2 is NOT_REACHED, so n3 must remain NOT_REACHED under ALL_SUCCESS
    trace = eng.execute(revision_id="r1")

    assert trace.nodes["n3"].node_status == NodeStatus.NOT_REACHED



def test_any_success_multi_parent_runs_when_one_parent_success():
    # n1 -> n3
    # n2 -> n3
    # Policy: ANY_SUCCESS for n3
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n3"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n3"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n3"),
        ],
        flow=[FlowRule(rule_id="fr1", node_id="n3", policy=FlowPolicy.ANY_SUCCESS)],
    )

    trace = eng.execute(revision_id="r1")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.NOT_REACHED
    assert trace.nodes["n3"].node_status == NodeStatus.SUCCESS



def test_first_success_behaves_like_any_success_in_v1():
    # v1: FIRST_SUCCESS is equivalent to ANY_SUCCESS (deterministic minimal semantics)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2", "n3"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n3"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n3"),
        ],
        flow=[FlowRule(rule_id="fr1", node_id="n3", policy=FlowPolicy.FIRST_SUCCESS)],
    )

    trace = eng.execute(revision_id="r1")
    assert trace.nodes["n3"].node_status == NodeStatus.SUCCESS
