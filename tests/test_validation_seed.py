from src.engine.engine import Engine
from src.engine.validation.validator import ValidationEngine


def test_current_v1_validator_does_not_enforce_seed():
    engine = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        meta={
            "determinism": True,
            "node_specs": {
                "n1": {
                    "provider_ref": "openai",
                    "model": "gpt",
                    "temperature": 0.1,
                    "seed": None,
                    "prompt_ref": "p1",
                }
            },
        },
    )

    result = ValidationEngine().validate(engine, revision_id="r1")

    rule_ids = {v.rule_id for v in result.violations}
    assert "DET-005" not in rule_ids
