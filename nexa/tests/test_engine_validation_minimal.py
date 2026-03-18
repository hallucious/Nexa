from __future__ import annotations

import pytest

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.validation.validator import ValidationEngine


def test_validation_fails_when_entry_missing():
    eng = Engine(entry_node_id="", node_ids=["n1"])
    v = ValidationEngine().validate(eng, revision_id="r1")
    assert v.success is False
    assert any(x.rule_id == "ENG-001" for x in v.violations)


def test_validation_fails_when_duplicate_node_id():
    eng = Engine(entry_node_id="n1", node_ids=["n1", "n1"])
    v = ValidationEngine().validate(eng, revision_id="r1")
    assert v.success is False
    assert any(x.rule_id == "NODE-001" for x in v.violations)


def test_validation_succeeds_for_minimal_valid_engine():
    # v1 minimal: only checks entry presence + duplicate ids for now
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )
    v = ValidationEngine().validate(eng, revision_id="r1")
    assert v.success is True
    assert v.violations == []
    assert v.engine_revision == "r1"
    assert isinstance(v.structural_fingerprint, str) and len(v.structural_fingerprint) >= 16
