from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.types import NodeStatus, StageStatus


def test_execute_marks_entry_success_when_validation_passes():
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )
    trace = eng.execute(revision_id="r1")

    assert trace.validation_success is True
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n1"].pre_status == StageStatus.SUCCESS
    assert trace.nodes["n1"].core_status == StageStatus.SUCCESS
    assert trace.nodes["n1"].post_status == StageStatus.SUCCESS

    # Others remain NOT_REACHED in v1 minimal semantics
    assert trace.nodes["n2"].node_status == NodeStatus.NOT_REACHED


def test_execute_does_not_mark_entry_when_validation_fails():
    # Missing entry triggers validation failure (ENG-001)
    eng = Engine(entry_node_id="", node_ids=["n1"])
    trace = eng.execute(revision_id="r1")

    assert trace.validation_success is False
    assert trace.nodes["n1"].node_status == NodeStatus.NOT_REACHED
