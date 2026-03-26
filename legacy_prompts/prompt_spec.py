from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import hashlib
import json
import re


_JSON_TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _stable_json_dumps(obj: Any) -> str:
    # Deterministic serialization for hashing.
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_object_schema(schema: Dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise ValueError("variables_schema.type must be 'object'")
    if "properties" not in schema or not isinstance(schema["properties"], dict):
        raise ValueError("variables_schema.properties must be a dict")
    if "required" in schema and not isinstance(schema["required"], list):
        raise ValueError("variables_schema.required must be a list if present")
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        raise ValueError("variables_schema.additionalProperties must be bool if present")


def _type_check(value: Any, json_type: str) -> bool:
    py_t = _JSON_TYPE_MAP.get(json_type)
    if py_t is None:
        # Unknown type: treat as pass-through for v1 minimal.
        return True
    # Note: bool is subclass of int; keep boolean strict.
    if json_type == "integer" and isinstance(value, bool):
        return False
    if json_type == "number" and isinstance(value, bool):
        return False
    return isinstance(value, py_t)


@dataclass(frozen=True)
class PromptSpec:
    prompt_id: str
    version: str
    template: str
    variables_schema: Dict[str, Any]
    description: str = ""

    def validate(self, variables: Dict[str, Any]) -> None:
        """Validate variables against a minimal JSON-Schema subset (v1.0.0).

        Supported subset:
        - type: object
        - properties: {name: {type: ...}}
        - required: [name, ...]
        - additionalProperties: false/true
        """
        if not isinstance(variables, dict):
            raise ValueError("variables must be a dict")

        schema = self.variables_schema
        if not isinstance(schema, dict):
            raise ValueError("variables_schema must be a dict")

        _validate_object_schema(schema)

        props: Dict[str, Any] = schema.get("properties", {})
        required: List[str] = schema.get("required", [])
        additional = schema.get("additionalProperties", True)

        # Required keys
        missing = [k for k in required if k not in variables]
        if missing:
            raise ValueError(f"missing required variables: {missing}")

        # Additional properties
        if additional is False:
            extra = [k for k in variables.keys() if k not in props]
            if extra:
                raise ValueError(f"unexpected variables: {extra}")

        # Type checks (only for declared properties)
        for name, rule in props.items():
            if name not in variables:
                continue
            if isinstance(rule, dict) and "type" in rule:
                jt = rule["type"]
                if isinstance(jt, str) and not _type_check(variables[name], jt):
                    raise ValueError(f"invalid type for '{name}': expected {jt}")

    def render(self, *, variables: Dict[str, Any]) -> str:
        self.validate(variables)

        rendered = self.template
        # Replace {{var}} occurrences for each provided variable.
        for k, v in variables.items():
            rendered = rendered.replace(f"{{{{{k}}}}}", str(v))

        # If template still contains unresolved {{...}}, treat as error.
        if re.search(r"\{\{[^}]+\}\}", rendered):
            raise ValueError("template contains unresolved variables")

        return rendered

    @property
    def prompt_hash(self) -> str:
        """Deterministic hash for linking/versioning.

        Format: 'sha256:<hex>'
        Input: template + stable-json(variables_schema)
        """
        base = self.template + _stable_json_dumps(self.variables_schema)
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
