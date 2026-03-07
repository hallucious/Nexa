
from src.platform.execution_config_schema import validate_execution_config_schema, ExecutionConfigSchemaError


def test_step125_valid_config():
    cfg = {
        "config_id": "summarize@1.0.0",
        "version": "1.0.0"
    }
    validate_execution_config_schema(cfg)


def test_step125_missing_config_id():
    try:
        validate_execution_config_schema({"version": "1.0.0"})
    except ExecutionConfigSchemaError:
        return
    assert False


def test_step125_wrong_pre_plugins_type():
    try:
        validate_execution_config_schema({
            "config_id": "x",
            "version": "1.0.0",
            "pre_plugins": "wrong"
        })
    except ExecutionConfigSchemaError:
        return
    assert False
