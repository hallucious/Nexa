from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.validation.validator import ValidationEngine


def test_validation_fails_when_cycle_detected():
    # n1 -> n2 -> n1 (cycle)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n1"),
        ],
    )

    v = ValidationEngine().validate(eng, revision_id="r1")

    assert v.success is False
    assert any(x.rule_id == "ENG-003" for x in v.violations)
