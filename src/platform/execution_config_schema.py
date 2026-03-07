
from typing import Dict, Any

class ExecutionConfigSchemaError(ValueError):
    pass


def validate_execution_config_schema(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ExecutionConfigSchemaError("ExecutionConfig must be a dict")

    if "config_id" not in payload:
        raise ExecutionConfigSchemaError("ExecutionConfig missing 'config_id'")

    if "version" not in payload:
        raise ExecutionConfigSchemaError("ExecutionConfig missing 'version'")

    if "pre_plugins" in payload and not isinstance(payload["pre_plugins"], list):
        raise ExecutionConfigSchemaError("'pre_plugins' must be a list")

    if "post_plugins" in payload and not isinstance(payload["post_plugins"], list):
        raise ExecutionConfigSchemaError("'post_plugins' must be a list")

    if "validation_rules" in payload and not isinstance(payload["validation_rules"], list):
        raise ExecutionConfigSchemaError("'validation_rules' must be a list")

    if "output_mapping" in payload and not isinstance(payload["output_mapping"], dict):
        raise ExecutionConfigSchemaError("'output_mapping' must be a dict")
