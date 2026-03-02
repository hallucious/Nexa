from __future__ import annotations

"""Step51: Validation → Trace Violation Structure Contract

Invariant:
- trace.validation_violations must be a list[dict] matching validation_engine_contract.md v1.2.0
- validation timestamp must be recorded in trace.meta.validation.at
"""

from src.engine.engine import Engine


def test_validation_violations_are_structured_dicts_and_timestamped():
    # invalid engine => validation failure (ENG-001)
    eng = Engine(entry_node_id="", node_ids=["n1"])
    trace = eng.execute(revision_id="r_invalid")

    assert trace.validation_success is False
    assert isinstance(trace.validation_violations, list)
    assert len(trace.validation_violations) >= 1

    v = trace.validation_violations[0]
    assert isinstance(v, dict)

    # required keys
    for k in ["rule_id", "rule_name", "severity", "location_type", "location_id", "message"]:
        assert k in v

    assert v["severity"] in ("error", "warning")

    # meta validation timestamp
    assert isinstance(trace.meta, dict)
    assert "validation" in trace.meta and isinstance(trace.meta["validation"], dict)
    assert isinstance(trace.meta["validation"].get("at"), str) and len(trace.meta["validation"]["at"]) >= 10
