"""test_step125 — Execution config schema. pre/post_plugins rejected."""
import pytest
from src.platform.execution_config_schema import validate_execution_config_schema, ExecutionConfigSchemaError


def test_step125_valid_config():
    validate_execution_config_schema({"config_id": "summarize@1.0.0", "version": "1.0.0"})


def test_step125_missing_config_id():
    with pytest.raises(ExecutionConfigSchemaError):
        validate_execution_config_schema({"version": "1.0.0"})


def test_step125_valid_plugins_list():
    validate_execution_config_schema({
        "config_id": "x", "version": "1.0.0", "plugins": ["sanitize.input"],
    })


def test_step125_wrong_plugins_type():
    with pytest.raises(ExecutionConfigSchemaError):
        validate_execution_config_schema({
            "config_id": "x", "version": "1.0.0", "plugins": "wrong",
        })


def test_step125_pre_plugins_rejected():
    with pytest.raises(ExecutionConfigSchemaError, match="pre_plugins"):
        validate_execution_config_schema({
            "config_id": "x", "version": "1.0.0", "pre_plugins": ["p1"],
        })


def test_step125_post_plugins_rejected():
    with pytest.raises(ExecutionConfigSchemaError, match="post_plugins"):
        validate_execution_config_schema({
            "config_id": "x", "version": "1.0.0", "post_plugins": ["p1"],
        })
