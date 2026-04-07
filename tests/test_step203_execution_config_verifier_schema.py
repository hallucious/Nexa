import pytest
import yaml

from src.platform.execution_config_registry import (
    ExecutionConfigModel,
    ExecutionConfigSchemaValidationError,
    ExecutionConfigSchemaValidator,
    load_execution_configs,
)


def test_step203_execution_config_model_accepts_verifier_object():
    model = ExecutionConfigModel.from_dict(
        {
            "config_id": "ec_example",
            "version": "1.0.0",
            "provider_ref": "openai",
            "verifier": {"verifier_id": "answer_quality"},
        }
    )
    assert model.verifier == {"verifier_id": "answer_quality"}


def test_step203_schema_validator_accepts_verifier_object(tmp_path):
    (tmp_path / "answer.yaml").write_text(
        yaml.safe_dump(
            {
                "config_id": "qa.answer",
                "version": "1.0.0",
                "provider_ref": "openai",
                "verifier": {"verifier_id": "answer_quality"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    registry = load_execution_configs(str(tmp_path))
    assert registry.get("qa.answer")["verifier"] == {"verifier_id": "answer_quality"}


def test_step203_schema_validator_rejects_non_object_verifier():
    with pytest.raises(ExecutionConfigSchemaValidationError, match="field 'verifier' must be an object"):
        ExecutionConfigSchemaValidator(
            {
                "config_id": "qa.answer",
                "version": "1.0.0",
                "provider_ref": "openai",
                "verifier": ["bad"],
            }
        ).validate()
