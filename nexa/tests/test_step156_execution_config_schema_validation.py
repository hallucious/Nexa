import pytest
import yaml

from src.config.execution_config_loader import load_execution_configs
from src.config.execution_config_schema_validator import (
    ExecutionConfigSchemaValidationError,
    ExecutionConfigSchemaValidator,
)


def test_step156_rejects_non_object_root():
    with pytest.raises(ExecutionConfigSchemaValidationError, match="root must be an object"):
        ExecutionConfigSchemaValidator([{"config_id": "x"}]).validate()


def test_step156_rejects_missing_config_id(tmp_path):
    path = tmp_path / "missing_config_id.yaml"
    path.write_text(yaml.safe_dump({"version": "1.0.0"}), encoding="utf-8")

    with pytest.raises(ExecutionConfigSchemaValidationError, match="missing_config_id.yaml"):
        load_execution_configs(str(tmp_path))


def test_step156_rejects_invalid_optional_string_field(tmp_path):
    path = tmp_path / "bad_provider.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "config_id": "qa.answer",
                "version": "1.0.0",
                "provider_ref": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ExecutionConfigSchemaValidationError,
        match="field 'provider_ref' must be a non-empty string",
    ):
        load_execution_configs(str(tmp_path))


def test_step156_rejects_invalid_plugin_list_type(tmp_path):
    path = tmp_path / "bad_pre_plugins.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "config_id": "qa.answer",
                "version": "1.0.0",
                "pre_plugins": "sanitize.input",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ExecutionConfigSchemaValidationError,
        match="field 'pre_plugins' must be a list",
    ):
        load_execution_configs(str(tmp_path))


def test_step156_rejects_unknown_field(tmp_path):
    path = tmp_path / "unknown_field.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "config_id": "qa.answer",
                "version": "1.0.0",
                "unexpected": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ExecutionConfigSchemaValidationError, match="unsupported field"):
        load_execution_configs(str(tmp_path))


def test_step156_rejects_duplicate_config_id_with_file_context(tmp_path):
    (tmp_path / "a.yaml").write_text(
        yaml.safe_dump({"config_id": "qa.answer", "version": "1.0.0"}),
        encoding="utf-8",
    )
    (tmp_path / "b.yaml").write_text(
        yaml.safe_dump({"config_id": "qa.answer", "version": "1.0.0"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="b.yaml: execution config already registered: qa.answer"):
        load_execution_configs(str(tmp_path))


def test_step156_accepts_valid_config_directory(tmp_path):
    (tmp_path / "answer.yaml").write_text(
        yaml.safe_dump(
            {
                "config_id": "qa.answer",
                "version": "1.0.0",
                "prompt_ref": "qa.prompt",
                "provider_ref": "openai",
                "pre_plugins": ["sanitize.input"],
                "post_plugins": ["format.output"],
                "validation_rules": ["non_empty"],
                "output_mapping": {"answer": "result.answer"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    registry = load_execution_configs(str(tmp_path))
    config = registry.get("qa.answer")

    assert config["config_id"] == "qa.answer"
    assert config["provider_ref"] == "openai"
    assert config["pre_plugins"] == ["sanitize.input"]