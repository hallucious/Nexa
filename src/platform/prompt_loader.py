from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Type

from .prompt_spec import PromptSpec, PromptSpecError


class PromptLoaderError(ValueError):
    """Raised when a PromptSpec cannot be loaded from disk."""


@dataclass(frozen=True)
class PromptFileHeader:
    """Optional JSON header format for future extension.

    If a prompt file starts with a line like:
      <!--PROMPT_SPEC: {...json...}-->
    we parse it and use it to fill id/version/inputs_schema/policy_tags/notes.
    The remainder of file becomes template.
    """

    id: str
    version: str
    inputs_schema: Dict[str, str]  # type names
    policy_tags: Optional[list[str]] = None
    notes: Optional[str] = None


_TYPE_MAP: Dict[str, Type[Any]] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


def _parse_header_line(line: str) -> Optional[PromptFileHeader]:
    line = line.strip()
    if not (line.startswith("<!--PROMPT_SPEC:") and line.endswith("-->")):
        return None
    payload = line[len("<!--PROMPT_SPEC:") : -len("-->")].strip()
    try:
        obj = __import__("json").loads(payload)
    except Exception as e:
        raise PromptLoaderError(f"Invalid PROMPT_SPEC header JSON: {e}") from e

    try:
        id_ = str(obj["id"])
        version = str(obj["version"])
        inputs_schema_raw = obj.get("inputs_schema", {}) or {}
        if not isinstance(inputs_schema_raw, dict):
            raise TypeError("inputs_schema must be an object")
        inputs_schema: Dict[str, str] = {str(k): str(v) for k, v in inputs_schema_raw.items()}
        policy_tags = obj.get("policy_tags")
        if policy_tags is not None and not isinstance(policy_tags, list):
            raise TypeError("policy_tags must be a list")
        notes = obj.get("notes")
        if notes is not None:
            notes = str(notes)
        return PromptFileHeader(id=id_, version=version, inputs_schema=inputs_schema, policy_tags=policy_tags, notes=notes)
    except Exception as e:
        raise PromptLoaderError(f"Invalid PROMPT_SPEC header fields: {e}") from e


def _infer_id_version_from_path(path: Path) -> tuple[str, str]:
    # Expected: prompts/<gate_name>/<version>.md
    # e.g. prompts/g1_design/v1.md -> id="g1_design/v1", version="v1"
    parts = path.parts
    if len(parts) >= 2:
        gate_name = parts[-2]
        version = path.stem
        return f"{gate_name}/{version}", version
    return f"{path.stem}/v1", "v1"


def load_prompt_spec(path: str | Path, inputs_schema: Optional[Mapping[str, Type[Any]]] = None) -> PromptSpec:
    """Load a PromptSpec from a prompt file.

    v0.1 behavior:
    - If PROMPT_SPEC header exists, it defines id/version/inputs_schema (as type names).
    - Otherwise, id/version are inferred from path; inputs_schema must be provided by caller.
    - Template is the remaining file content.
    """
    p = Path(path)
    if not p.exists():
        raise PromptLoaderError(f"Prompt file not found: {p}")

    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()

    header = _parse_header_line(lines[0]) if lines else None
    if header is not None:
        # Convert type-name schema to python types
        schema: Dict[str, Type[Any]] = {}
        for k, tname in header.inputs_schema.items():
            if tname not in _TYPE_MAP:
                raise PromptLoaderError(f"Unsupported type in inputs_schema: {k}={tname}")
            schema[k] = _TYPE_MAP[tname]
        template = "\n".join(lines[1:]).lstrip("\n")
        return PromptSpec(
            id=header.id,
            version=header.version,
            template=template,
            inputs_schema=schema,
            policy_tags=header.policy_tags,
            notes=header.notes,
        )

    # No header: infer id/version; require inputs_schema passed in
    if inputs_schema is None:
        raise PromptLoaderError("inputs_schema is required when PROMPT_SPEC header is absent")
    id_, version = _infer_id_version_from_path(p)
    return PromptSpec(id=id_, version=version, template=text, inputs_schema=dict(inputs_schema))
