"""
Prompt schema + validation utilities.

This module is part of "PromptStore v1 upgrade" hardening:
- Prompt definitions are versioned, schema-validated objects (not loose text).
- Render inputs are validated against prompt-declared input_schema before templating.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Optional

try:
    # Prefer Pydantic v2 if available
    from pydantic import BaseModel, Field, ValidationError, field_validator
except Exception:  # pragma: no cover
    # Fallback to Pydantic v1
    from pydantic import BaseModel, Field, ValidationError, validator as field_validator  # type: ignore


class PromptDefinition(BaseModel):
    """
    Canonical prompt definition format.

    This is intentionally minimal and strict.
    Expand ONLY when needed and reflected in BLUEPRINT/CODING_PLAN.
    """

    name: str = Field(..., min_length=1, description="Stable prompt name, e.g., 'g2_continuity'")
    version: str = Field(..., min_length=1, description="Semver-ish string, e.g., '1.0'")
    description: Optional[str] = Field(None, description="Human-readable description")
    # JSON Schema for runtime input validation before rendering.
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for render inputs")
    # Template text (renderer uses this)
    template: str = Field(..., min_length=1, description="Prompt template text")

    @field_validator("name")
    def _name_no_whitespace(cls, v: str) -> str:  # type: ignore
        if v.strip() != v:
            raise ValueError("name must not have leading/trailing whitespace")
        return v

    @field_validator("version")
    def _version_no_whitespace(cls, v: str) -> str:  # type: ignore
        if v.strip() != v:
            raise ValueError("version must not have leading/trailing whitespace")
        return v

    @field_validator("input_schema")
    def _input_schema_minimal(cls, v: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        # Minimal guardrails so we don't accept nonsense schemas.
        if not isinstance(v, dict):
            raise ValueError("input_schema must be an object/dict")
        schema_type = v.get("type")
        if schema_type is None:
            # Allow schema without "type" only if it looks like a valid JSON schema (has properties or anyOf etc).
            if not any(k in v for k in ("properties", "anyOf", "oneOf", "allOf", "$ref")):
                raise ValueError("input_schema must include 'type' or schema composition/structure keys")
        return v


@dataclass(frozen=True)
class PromptIdentity:
    """Computed identity metadata for auditing/tracing."""

    name: str
    version: str
    sha256: str

    @property
    def sha256_prefixed(self) -> str:
        return f"sha256:{self.sha256}"


def _stable_hash_text(text: str) -> str:
    h = sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def compute_prompt_identity(defn: PromptDefinition) -> PromptIdentity:
    """
    Compute prompt identity hash.

    Hash includes: name, version, input_schema, template (and description if present).
    This is deliberate: any meaningful prompt change changes identity.
    """
    payload = {
        "name": defn.name,
        "version": defn.version,
        "description": defn.description,
        "input_schema": defn.input_schema,
        "template": defn.template,
    }
    # Stable canonical serialization (no external dependency)
    # We avoid json.dumps sort_keys=False; enforce sort_keys=True for stability.
    import json

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return PromptIdentity(defn.name, defn.version, _stable_hash_text(canonical))


class PromptValidationError(ValueError):
    """Raised when a prompt definition fails validation."""


class PromptInputValidationError(ValueError):
    """Raised when render inputs fail prompt-declared schema validation."""


def validate_prompt_definition(data: Any) -> PromptDefinition:
    """
    Validate a raw prompt definition (dict or JSON-decoded object).

    Raises PromptValidationError on failure.
    Returns PromptDefinition on success.
    """
    try:
        return PromptDefinition.model_validate(data)  # pydantic v2
    except AttributeError:  # pragma: no cover
        try:
            return PromptDefinition.parse_obj(data)  # pydantic v1
        except ValidationError as e:
            raise PromptValidationError(str(e)) from e
    except ValidationError as e:
        raise PromptValidationError(str(e)) from e


def _jsonschema_validate(schema: Dict[str, Any], instance: Dict[str, Any]) -> None:
    """
    Validate instance against JSON Schema using jsonschema if installed.

    We keep this import local so the repo can run without jsonschema,
    but tests/production should include it for strict validation.
    """
    try:
        import jsonschema  # type: ignore
    except Exception as e:  # pragma: no cover
        raise PromptInputValidationError(
            "jsonschema package is required for input_schema validation. "
            "Install 'jsonschema' to enable strict validation."
        ) from e

    try:
        jsonschema.validate(instance=instance, schema=schema)
    except Exception as e:
        raise PromptInputValidationError(str(e)) from e


def validate_render_input(defn: PromptDefinition, inputs: Dict[str, Any]) -> None:
    """
    Validate render inputs against defn.input_schema.

    Raises PromptInputValidationError on failure.
    """
    if not isinstance(inputs, dict):
        raise PromptInputValidationError("render inputs must be a dict/object")
    _jsonschema_validate(defn.input_schema, inputs)
