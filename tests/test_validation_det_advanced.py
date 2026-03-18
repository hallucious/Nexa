from src.engine.engine import Engine
from src.engine.validation.validator import ValidationEngine


def test_current_v1_validator_does_not_enforce_model_or_temperature():
    engine = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        meta={
            "determinism": True,
            "node_specs": {
                "n1": {
                    "provider_ref": "openai",
                    "model": None,
                    "temperature": None,
                    "prompt_ref": "p1",
                }
            },
        },
    )

    result = ValidationEngine().validate(engine, revision_id="r1")

    rule_ids = {v.rule_id for v in result.violations}
    assert "DET-003" not in rule_ids
    assert "DET-004" not in rule_ids
