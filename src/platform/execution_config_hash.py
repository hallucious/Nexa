from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


HASH_EXCLUDED_TOP_LEVEL_FIELDS = {
    "config_id",
    "label",
    "description",
    "notes",
    "created_at",
    "updated_at",
    "version",
}


def _drop_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            cleaned = _drop_nulls(v)
            if cleaned is not None:
                out[k] = cleaned
        return out
    if isinstance(value, list):
        return [_drop_nulls(v) for v in value]
    return value


def canonicalize_execution_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config, dict):
        raise TypeError("config must be dict")

    canonical: Dict[str, Any] = {}
    for key, value in config.items():
        if key in HASH_EXCLUDED_TOP_LEVEL_FIELDS:
            continue
        if key == "runtime_config":
            if value is None:
                continue
            if not isinstance(value, dict):
                raise TypeError("runtime_config must be dict")
            execution_cfg = value.get("execution", {})
            if execution_cfg is None:
                execution_cfg = {}
            if not isinstance(execution_cfg, dict):
                raise TypeError("runtime_config.execution must be dict")
            canonical[key] = {"execution": _drop_nulls(execution_cfg)}
            continue
        canonical[key] = _drop_nulls(value)

    if "config_schema_version" not in canonical:
        canonical["config_schema_version"] = "1"

    return canonical


def canonicalize_execution_config_json(config: Dict[str, Any]) -> str:
    canonical = canonicalize_execution_config(config)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_execution_config_hash(config: Dict[str, Any]) -> str:
    canonical_json = canonicalize_execution_config_json(config)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def generate_execution_config_id(config: Dict[str, Any], *, prefix: str = "ec", short_length: int = 8) -> str:
    if short_length <= 0:
        raise ValueError("short_length must be positive")
    digest = compute_execution_config_hash(config)
    return f"{prefix}_{digest[:short_length]}"
