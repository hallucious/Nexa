from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
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
