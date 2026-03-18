from __future__ import annotations

from typing import Any, Dict, Set


class ExecutionConfigSchemaValidationError(ValueError):
    """Raised when an execution config file fails static schema validation."""


class ExecutionConfigSchemaValidator:
    """
    Step156

    Performs static/schema validation for execution config payloads before they
    enter the registry.
    """

    ALLOWED_FIELDS: Set[str] = {
        "config_id",
        "version",
        "prompt_ref",
        "prompt_inputs",
        "provider_ref",
        "provider_inputs",
        "pre_plugins",
        "post_plugins",
        "validation_rules",
        "output_mapping",
        "runtime_config",
    }

    def __init__(self, payload: Any):
        self.payload = payload

    def validate(self) -> Dict[str, Any]:
        if not isinstance(self.payload, dict):
            raise ExecutionConfigSchemaValidationError(
                "execution config root must be an object"
            )

        payload = self.payload
        self._validate_allowed_fields(payload)
        self._validate_required_string_field(payload, "config_id")
        self._validate_optional_string_field(payload, "version")
        self._validate_optional_string_field(payload, "prompt_ref")
        self._validate_optional_string_dict_field(payload, "prompt_inputs")
        self._validate_optional_string_field(payload, "provider_ref")
        self._validate_optional_string_dict_field(payload, "provider_inputs")
        self._validate_optional_string_list_field(payload, "pre_plugins")
        self._validate_optional_string_list_field(payload, "post_plugins")
        self._validate_optional_string_list_field(payload, "validation_rules")
        self._validate_output_mapping(payload)
        self._validate_runtime_config(payload)
        return payload

    def _validate_allowed_fields(self, payload: Dict[str, Any]) -> None:
        unknown = sorted(set(payload.keys()) - self.ALLOWED_FIELDS)
        if unknown:
            raise ExecutionConfigSchemaValidationError(
                "execution config contains unsupported field(s): " + ", ".join(unknown)
            )

    def _validate_required_string_field(self, payload: Dict[str, Any], field_name: str) -> None:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ExecutionConfigSchemaValidationError(
                f"execution config missing valid string field: {field_name}"
            )

    def _validate_optional_string_field(self, payload: Dict[str, Any], field_name: str) -> None:
        if field_name not in payload:
            return

        value = payload[field_name]
        if not isinstance(value, str) or not value.strip():
            raise ExecutionConfigSchemaValidationError(
                f"execution config field '{field_name}' must be a non-empty string"
            )


    def _validate_optional_string_dict_field(self, payload: Dict[str, Any], field_name: str) -> None:
        if field_name not in payload:
            return

        value = payload[field_name]
        if not isinstance(value, dict):
            raise ExecutionConfigSchemaValidationError(
                f"execution config field '{field_name}' must be an object"
            )

        for key, item in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ExecutionConfigSchemaValidationError(
                    f"execution config field '{field_name}' contains invalid key"
                )
            if not isinstance(item, str) or not item.strip():
                raise ExecutionConfigSchemaValidationError(
                    f"execution config field '{field_name}' has invalid value for key '{key}'"
                )

    def _validate_optional_string_list_field(self, payload: Dict[str, Any], field_name: str) -> None:
        if field_name not in payload:
            return

        value = payload[field_name]
        if not isinstance(value, list):
            raise ExecutionConfigSchemaValidationError(
                f"execution config field '{field_name}' must be a list"
            )

        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ExecutionConfigSchemaValidationError(
                    f"execution config field '{field_name}' has invalid entry at index {index}"
                )

    def _validate_output_mapping(self, payload: Dict[str, Any]) -> None:
        if "output_mapping" not in payload:
            return

        output_mapping = payload["output_mapping"]
        if not isinstance(output_mapping, dict):
            raise ExecutionConfigSchemaValidationError(
                "execution config field 'output_mapping' must be an object"
            )

        for key, value in output_mapping.items():
            if not isinstance(key, str) or not key.strip():
                raise ExecutionConfigSchemaValidationError(
                    "execution config field 'output_mapping' contains invalid key"
                )
            if not isinstance(value, str) or not value.strip():
                raise ExecutionConfigSchemaValidationError(
                    f"execution config field 'output_mapping' has invalid value for key '{key}'"
                )
    def _validate_runtime_config(self, payload: Dict[str, Any]) -> None:
        if "runtime_config" not in payload:
            return

        runtime_config = payload["runtime_config"]
        if not isinstance(runtime_config, dict):
            raise ExecutionConfigSchemaValidationError(
                "execution config field 'runtime_config' must be an object"
            )
