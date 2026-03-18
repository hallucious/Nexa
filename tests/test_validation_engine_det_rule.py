from __future__ import annotations

from types import SimpleNamespace

from src.engine.validation.validator import ValidationEngine


def _fingerprint_stub(_structure):
    return SimpleNamespace(value="fp-test")


class _FakeEngine:
    def __init__(self, structure):
        self._structure = structure

    def to_structure(self):
        return self._structure


def test_validation_engine_current_v1_does_not_enforce_det_001(monkeypatch):
    from src.engine.validation import validator as validator_module

    monkeypatch.setattr(validator_module, "compute_fingerprint", _fingerprint_stub)

    structure = SimpleNamespace(
        entry_node_id="n1",
        node_ids=["n1"],
        channels=[],
        flow=[],
        meta={},
    )
    engine = _FakeEngine(structure)

    result = ValidationEngine().validate(engine, revision_id="rev-1")

    assert result.success is True
    assert "DET-001" not in result.applied_rule_ids
    assert all(v.rule_id != "DET-001" for v in result.violations)


def test_validation_engine_current_v1_ignores_determinism_meta(monkeypatch):
    from src.engine.validation import validator as validator_module

    monkeypatch.setattr(validator_module, "compute_fingerprint", _fingerprint_stub)

    structure = SimpleNamespace(
        entry_node_id="n1",
        node_ids=["n1"],
        channels=[],
        flow=[],
        meta={"determinism": True},
    )
    engine = _FakeEngine(structure)

    result = ValidationEngine().validate(engine, revision_id="rev-1")

    assert result.success is True
    assert "DET-001" not in result.applied_rule_ids
    assert all(v.rule_id != "DET-001" for v in result.violations)
