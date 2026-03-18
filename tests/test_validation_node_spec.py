from src.engine.engine import Engine
from src.engine.validation.validator import ValidationEngine


def test_current_v1_validator_ignores_node_specs_det_fields():
    engine = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        meta={
            "determinism": True,
            "node_specs": {
                "n1": {
                    "provider_ref": None,
                    "prompt_ref": None,
                }
            },
        },
    )

    result = ValidationEngine().validate(engine, revision_id="r1")

    rule_ids = {v.rule_id for v in result.violations}
    assert "DET-002" not in rule_ids
    assert "DET-006" not in rule_ids
