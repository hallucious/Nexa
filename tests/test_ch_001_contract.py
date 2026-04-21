from __future__ import annotations

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.validation.validator import ValidationEngine


def test_ch_001_channel_references_missing_node():
    eng = Engine(
        entry_node_id="a",
        node_ids=["a"],
        channels=[Channel(channel_id="c1", src_node_id="a", dst_node_id="b")],
    )
    res = ValidationEngine().validate(eng, revision_id="r-ch-001")
    ids = {v.rule_id for v in res.violations}
    assert "CH-001" in ids
