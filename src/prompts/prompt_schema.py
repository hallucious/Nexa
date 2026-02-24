"""
Prompt schema + validation utilities.

This module hardens PromptStore/Renderer:
- Prompt definitions are versioned, schema-validated objects (not loose text).
- Render inputs are validated against prompt-declared input_schema before rendering.

Design goal:
- **No heavy runtime dependencies** (avoid pydantic) to keep the repo portable.
- JSON Schema validation uses `jsonschema` when installed (recommended & pinned in requirements).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Optional


# -----------------------------
# Core data model (no pydantic)
# -----------------------------

@dataclass(frozen=True)
class PromptDefinition:
    """Canonical prompt definition (strict, minimal)."""

    name: str
    version: str
    description: Optional[str]
    input_schema: Dict[str, Any]
    template: str


@dataclass(frozen=True)
class PromptIdentity:
    """Computed identity metadata for auditing/tracing."""

    name: str
    version: str
    sha256: str

    @property
    def sha256_prefixed(self) -> str:
        return f"sha256:{self.sha256}"


class PromptValidationError(ValueError):
    """Raised when a prompt definition fails validation."""


class PromptInputValidationError(ValueError):
    """Raised when render inputs fail prompt-declared schema validation."""


# -----------------------------
# Identity / hashing
# -----------------------------

def _stable_hash_text(text: str) -> str:
    h = sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def compute_prompt_identity(defn: PromptDefinition) -> PromptIdentity:
    """
    Compute prompt identity hash.

    Hash includes: name, version, input_schema, template (and description if present).
    Any meaningful prompt change changes identity.
    """
    payload = {
        "name": defn.name,
        "version": defn.version,
        "description": defn.description,
        "input_schema": defn.input_schema,
        "template": defn.template,
    }
    import json

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return PromptIdentity(defn.name, defn.version, _stable_hash_text(canonical))


# -----------------------------
# Validation
# -----------------------------

def _require_str(data: Dict[str, Any], key: str) -> str:
    v = data.get(key)
    if not isinstance(v, str):
        raise PromptValidationError(f"{key} must be a string")
    # Reject empty / all-whitespace strings
    if not v.strip():
        raise PromptValidationError(f"{key} must be a non-empty string")
    # Leading whitespace is almost always accidental and makes templates hard to read.
    # Trailing newlines are common in prompt files; allow them.
    if v.lstrip() != v:
        raise PromptValidationError(f"{key} must not have leading whitespace")
    return v


def _require_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    v = data.get(key)
    if not isinstance(v, dict):
        raise PromptValidationError(f"{key} must be an object/dict")
    return v


def validate_prompt_definition(data: Any) -> PromptDefinition:
    """
    Validate a raw prompt definition (dict or JSON-decoded object).

    Raises PromptValidationError on failure.
    Returns PromptDefinition on success.
    """
    if not isinstance(data, dict):
        raise PromptValidationError("prompt definition must be an object/dict")

    name = _require_str(data, "name")
    version = _require_str(data, "version")
    template = _require_str(data, "template")

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        raise PromptValidationError("description must be a string if provided")

    input_schema = _require_dict(data, "input_schema")
    # Minimal guardrails to avoid nonsense schemas.
    schema_type = input_schema.get("type")
    if schema_type is None:
        if not any(k in input_schema for k in ("properties", "anyOf", "oneOf", "allOf", "$ref")):
            raise PromptValidationError("input_schema must include 'type' or schema structure keys")

    return PromptDefinition(
        name=name,
        version=version,
        description=description,
        input_schema=input_schema,
        template=template,
    )


def _jsonschema_validate(schema: Dict[str, Any], instance: Dict[str, Any]) -> None:
    """Validate instance against JSON Schema using jsonschema (required)."""
    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise PromptInputValidationError(
            "jsonschema package is required for input_schema validation. "
            "Install it via: pip install -r requirements.txt"
        ) from e

    try:
        jsonschema.validate(instance=instance, schema=schema)
    except Exception as e:
        raise PromptInputValidationError(str(e)) from e


def validate_render_input(defn: PromptDefinition, inputs: Dict[str, Any]) -> None:
    """Validate render inputs against defn.input_schema."""
    if not isinstance(inputs, dict):
        raise PromptInputValidationError("render inputs must be a dict/object")
    _jsonschema_validate(defn.input_schema, inputs)
