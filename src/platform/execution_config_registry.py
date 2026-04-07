
from __future__ import annotations

import json

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.engine.execution_config_hash import generate_execution_config_id


class ExecutionConfigRegistryError(Exception):
    """Base class for execution config registry errors."""


class ExecutionConfigRefError(ExecutionConfigRegistryError):
    """Raised when execution_config_ref format is invalid."""


class ExecutionConfigNotFoundError(ExecutionConfigRegistryError):
    """Raised when config_id directory does not exist."""


class ExecutionConfigVersionError(ExecutionConfigRegistryError):
    """Raised when version file resolution fails for an existing config_id."""


class ExecutionConfigFormatError(ExecutionConfigRegistryError):
    """Raised when registry JSON is malformed or semantically invalid."""


@dataclass(frozen=True)
class ExecutionConfigModel:
    config_id: str
    version: str
    config_schema_version: str = "1"
    label: Optional[str] = None
    inputs: Dict[str, str] = field(default_factory=dict)
    plugins: list[str] = field(default_factory=list)
    prompt_ref: Optional[str] = None
    provider_ref: Optional[str] = None
    validation_rules: list[str] = field(default_factory=list)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    verifier: Dict[str, Any] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)
    runtime_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ExecutionConfigModel":
        if not isinstance(payload, dict):
            raise ExecutionConfigFormatError("execution config payload must be dict")

        config_id = payload.get("config_id")
        version = payload.get("version")
        if not isinstance(config_id, str) or not config_id:
            raise ExecutionConfigFormatError("config_id must be non-empty string")
        if not isinstance(version, str) or not version:
            raise ExecutionConfigFormatError("version must be non-empty string")

        def _dict_str_str(value: Any, field_name: str) -> Dict[str, str]:
            if value is None:
                return {}
            if not isinstance(value, dict):
                raise ExecutionConfigFormatError(f"{field_name} must be dict[str, str]")
            out: Dict[str, str] = {}
            for k, v in value.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ExecutionConfigFormatError(f"{field_name} must be dict[str, str]")
                out[k] = v
            return out

        def _list_str(value: Any, field_name: str) -> list[str]:
            if value is None:
                return []
            if not isinstance(value, list):
                raise ExecutionConfigFormatError(f"{field_name} must be list[str]")
            out: list[str] = []
            for item in value:
                if not isinstance(item, str):
                    raise ExecutionConfigFormatError(f"{field_name} entries must be string")
                out.append(item)
            return out

        label = payload.get("label")
        if label is not None and not isinstance(label, str):
            raise ExecutionConfigFormatError("label must be string when present")

        prompt_ref = payload.get("prompt_ref")
        if prompt_ref is not None and not isinstance(prompt_ref, str):
            raise ExecutionConfigFormatError("prompt_ref must be string when present")

        provider_ref = payload.get("provider_ref")
        if provider_ref is not None and not isinstance(provider_ref, str):
            raise ExecutionConfigFormatError("provider_ref must be string when present")

        verifier = payload.get("verifier") or {}
        if not isinstance(verifier, dict):
            raise ExecutionConfigFormatError("verifier must be dict")

        policy = payload.get("policy") or {}
        if not isinstance(policy, dict):
            raise ExecutionConfigFormatError("policy must be dict")

        runtime_config = payload.get("runtime_config") or {}
        if not isinstance(runtime_config, dict):
            raise ExecutionConfigFormatError("runtime_config must be dict")

        for _legacy in ("pre_plugins", "post_plugins"):
            if payload.get(_legacy) is not None:
                raise ExecutionConfigFormatError(
                    f"'{_legacy}' is not a valid execution config field. Use 'plugins' instead."
                )

        active_slots = [
            bool(prompt_ref),
            bool(provider_ref),
            bool(payload.get("plugins")),
            bool(payload.get("validation_rules")),
        ]
        if not any(active_slots):
            raise ExecutionConfigFormatError(
                "execution config must activate at least one slot: plugins, prompt_ref, provider_ref, validation_rules"
            )

        return cls(
            config_id=config_id,
            version=version,
            config_schema_version=str(payload.get("config_schema_version") or "1"),
            label=label,
            inputs=_dict_str_str(payload.get("inputs"), "inputs"),
            plugins=_list_str(payload.get("plugins"), "plugins"),
            prompt_ref=prompt_ref,
            provider_ref=provider_ref,
            validation_rules=_list_str(payload.get("validation_rules"), "validation_rules"),
            output_mapping=_dict_str_str(payload.get("output_mapping"), "output_mapping"),
            verifier=dict(verifier),
            policy=dict(policy),
            runtime_config=dict(runtime_config),
        )


def parse_execution_config_ref(ref: str) -> Tuple[str, Optional[str]]:
    if not isinstance(ref, str) or not ref:
        raise ExecutionConfigRefError("execution_config_ref must be non-empty string")
    parts = ref.split(":")
    if len(parts) == 1 and parts[0]:
        return parts[0], None
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[0], parts[1]
    raise ExecutionConfigRefError(
        "execution_config_ref must have form '<config_id>' or '<config_id>:<version>'"
    )


class ExecutionConfigRegistry:
    def __init__(self, root: str | Path = "registry/execution_configs"):
        self.root = Path(root)
        self._cache: Dict[Tuple[str, str], ExecutionConfigModel] = {}

    def _resolve_path(self, config_id: str, version: Optional[str]) -> Path:
        config_dir = self.root / config_id
        if not config_dir.exists():
            raise ExecutionConfigNotFoundError(f"Unknown execution config id: {config_id}")

        if version is not None:
            path = config_dir / f"{version}.json"
            if not path.exists():
                raise ExecutionConfigVersionError(f"Unknown version for {config_id}: {version}")
            return path

        matches = sorted(config_dir.glob("*.json"))
        if not matches:
            raise ExecutionConfigVersionError(f"No version files found for {config_id}")
        if len(matches) > 1:
            raise ExecutionConfigVersionError(
                f"Ambiguous version for {config_id}: exact version required when multiple files exist"
            )
        return matches[0]

    def resolve(self, ref: str) -> ExecutionConfigModel:
        config_id, version = parse_execution_config_ref(ref)
        cache_version = version or "__single__"
        key = (config_id, cache_version)
        if key in self._cache:
            return self._cache[key]

        path = self._resolve_path(config_id, version)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            ref_desc = f"{config_id}:{version}" if version else config_id
            raise ExecutionConfigFormatError(f"Invalid JSON for {ref_desc}: {e}") from e

        model = ExecutionConfigModel.from_dict(payload)

        expected_id = generate_execution_config_id(payload)
        if model.config_id != expected_id:
            raise ExecutionConfigFormatError(
                f"config_id mismatch: expected {expected_id}, found {model.config_id}"
            )
        if model.config_id != config_id:
            raise ExecutionConfigFormatError(
                f"config_id mismatch: ref={config_id}, file={model.config_id}"
            )
        if version is not None and model.version != version:
            raise ExecutionConfigFormatError(
                f"version mismatch: ref={version}, file={model.version}"
            )

        self._cache[key] = model
        return model

    def get(self, config_id: str) -> Optional[ExecutionConfigModel]:
        try:
            return self.resolve(config_id)
        except (ExecutionConfigNotFoundError, ExecutionConfigVersionError, ExecutionConfigFormatError):
            return None


_default_registry = ExecutionConfigRegistry()


def resolve_execution_config(ref: str, *, registry: Optional[ExecutionConfigRegistry] = None) -> ExecutionConfigModel:
    reg = registry or _default_registry
    return reg.resolve(ref)


class ExecutionConfigSchemaValidationError(ValueError):
    """Raised when a YAML execution config file fails static validation."""


class ExecutionConfigSchemaValidator:
    """Static validator for legacy/simple execution config payloads."""

    ALLOWED_FIELDS = {
        "config_id",
        "version",
        "prompt_ref",
        "prompt_inputs",
        "provider_ref",
        "provider_inputs",
        "plugins",
        "validation_rules",
        "output_mapping",
        "verifier",
        "runtime_config",
    }

    def __init__(self, payload: Any):
        self.payload = payload

    def validate(self) -> Dict[str, Any]:
        if not isinstance(self.payload, dict):
            raise ExecutionConfigSchemaValidationError("execution config root must be an object")

        payload = self.payload
        self._validate_allowed_fields(payload)
        self._validate_required_string_field(payload, "config_id")
        self._validate_optional_string_field(payload, "version")
        self._validate_optional_string_field(payload, "prompt_ref")
        self._validate_optional_string_dict_field(payload, "prompt_inputs")
        self._validate_optional_string_field(payload, "provider_ref")
        self._validate_optional_string_dict_field(payload, "provider_inputs")
        self._validate_optional_string_list_field(payload, "plugins")
        self._validate_optional_string_list_field(payload, "validation_rules")
        self._validate_output_mapping(payload)
        self._validate_verifier(payload)
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

    def _validate_verifier(self, payload: Dict[str, Any]) -> None:
        if "verifier" not in payload:
            return
        verifier = payload["verifier"]
        if not isinstance(verifier, dict):
            raise ExecutionConfigSchemaValidationError(
                "execution config field 'verifier' must be an object"
            )

    def _validate_runtime_config(self, payload: Dict[str, Any]) -> None:
        if "runtime_config" not in payload:
            return
        runtime_config = payload["runtime_config"]
        if not isinstance(runtime_config, dict):
            raise ExecutionConfigSchemaValidationError(
                "execution config field 'runtime_config' must be an object"
            )


class AdhocExecutionConfigRegistry:
    """Mutable registry used by CLI/simple YAML execution config loading."""

    def __init__(self):
        self._configs: Dict[str, dict] = {}

    def register(self, config: dict):
        if "config_id" not in config:
            raise ValueError("execution config must contain config_id")
        config_id = config["config_id"]
        if config_id in self._configs:
            raise ValueError(f"execution config already registered: {config_id}")
        self._configs[config_id] = config

    def get(self, config_id: str) -> dict:
        if config_id not in self._configs:
            raise KeyError(f"execution config not found: {config_id}")
        return self._configs[config_id]

    def list_configs(self):
        return list(self._configs.keys())


def load_execution_configs(config_dir: str | Path) -> AdhocExecutionConfigRegistry:
    registry = AdhocExecutionConfigRegistry()
    path = Path(config_dir)
    if not path.exists():
        raise FileNotFoundError(str(config_dir))

    for file in sorted(path.glob("*.yaml")):
        with open(file, "r", encoding="utf-8") as f:
            loaded: Any = yaml.safe_load(f)

        try:
            config = ExecutionConfigSchemaValidator(loaded).validate()
            registry.register(config)
        except ExecutionConfigSchemaValidationError as exc:
            raise ExecutionConfigSchemaValidationError(f"{file.name}: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"{file.name}: {exc}") from exc

    return registry
