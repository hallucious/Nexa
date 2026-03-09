
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Type

from src.platform.prompt_spec import PromptSpec


class PromptLoaderError(Exception):
    pass


HEADER_PATTERN = re.compile(
    r"^<!--PROMPT_SPEC:\s*(\{.*\})\s*-->",
    re.DOTALL,
)


_TYPE_MAP: Dict[str, Type[Any]] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


def _parse_schema(schema: Dict[str, Any]) -> Dict[str, Type[Any]]:
    parsed: Dict[str, Type[Any]] = {}
    for k, v in schema.items():
        if isinstance(v, str):
            if v not in _TYPE_MAP:
                raise PromptLoaderError(f"Unsupported schema type: {v}")
            parsed[k] = _TYPE_MAP[v]
        elif isinstance(v, type):
            parsed[k] = v
        else:
            raise PromptLoaderError(f"Invalid schema entry for {k}: {v}")
    return parsed


def _infer_id_and_version(path: Path):
    try:
        version = path.stem
        prompt_dir = path.parent.name
        return f"{prompt_dir}/{version}", version
    except Exception:
        raise PromptLoaderError(f"Cannot infer id/version from path: {path}")


def load_prompt_spec(
    path: Path,
    inputs_schema: Optional[Dict[str, Type[Any]]] = None,
) -> PromptSpec:

    p = Path(path)

    try:
        raw = p.read_text(encoding="utf-8")
    except Exception as e:
        raise PromptLoaderError(f"Failed to read prompt file: {p}") from e

    header_match = HEADER_PATTERN.match(raw)

    header_data = None
    template = raw

    if header_match:
        try:
            header_json = header_match.group(1)
            header_data = json.loads(header_json)
        except Exception as e:
            raise PromptLoaderError("Invalid PROMPT_SPEC header JSON") from e

        template = raw[header_match.end():].lstrip("\n")

    if header_data:
        pid = header_data.get("id")
        version = header_data.get("version")

        if not pid or not version:
            raise PromptLoaderError("PROMPT_SPEC header must contain id and version")

        schema_raw = header_data.get("inputs_schema", {})
        schema = _parse_schema(schema_raw)

    else:
        if inputs_schema is None:
            raise PromptLoaderError(
                "inputs_schema required when PROMPT_SPEC header is absent"
            )

        pid, version = _infer_id_and_version(p)
        schema = inputs_schema

    return PromptSpec(
        id=pid,
        version=version,
        template=template,
        inputs_schema=schema,
    )
