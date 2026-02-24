from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import re

from .registry import PROMPT_REGISTRY
from .prompt_schema import PromptDefinition, compute_prompt_identity, validate_prompt_definition


class PromptStore:
    """Load prompt templates.

    Backward compatible:
    - Versioned IDs: "g7_final_review@v1" (preferred)
    - Legacy filenames: "g7_final_review.prompt.txt" (supported but discouraged)

    New strict API:
    - get_definition(prompt_id) -> PromptDefinition
    - get_identity(prompt_id) -> PromptIdentity
    """

    BASE_DIR = Path(__file__).parent

    @classmethod
    def load(cls, key: str) -> str:
        # Versioned ID path
        if key in PROMPT_REGISTRY:
            file_name = PROMPT_REGISTRY[key]["file"]
            path = cls.BASE_DIR / file_name
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found for id '{key}': {path}")
            return path.read_text(encoding="utf-8")

        # Legacy filename path (kept for tests and incremental migration)
        if key.endswith(".prompt.txt") or key.endswith(".txt"):
            path = cls.BASE_DIR / key
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            return path.read_text(encoding="utf-8")

        raise ValueError(f"Unknown prompt key (not in registry and not a filename): {key}")

    @classmethod
    def _parse_prompt_id(cls, prompt_id: str) -> Tuple[str, str]:
        if "@" not in prompt_id:
            raise ValueError(
                "prompt_id must be versioned like 'name@v1' (version is mandatory). Got: %s" % prompt_id
            )
        name, version = prompt_id.split("@", 1)
        name = name.strip()
        version = version.strip()
        if not name or not version:
            raise ValueError(f"prompt_id must include non-empty name and version: {prompt_id}")
        return name, version

    @classmethod
    def _build_default_input_schema_from_template(cls, template: str) -> Dict[str, Any]:
        # Conservative: all placeholders in template must be present, and values must be strings.
        placeholders = sorted(set(re.findall(r"{{\s*(\w+)\s*}}", template)))
        return {
            "type": "object",
            "properties": {k: {"type": "string"} for k in placeholders},
            "required": placeholders,
            "additionalProperties": False,
        }

    @classmethod
    def get_definition(cls, prompt_id: str) -> PromptDefinition:
        if prompt_id not in PROMPT_REGISTRY:
            raise ValueError(f"Unknown prompt id: {prompt_id}")
        name, version = cls._parse_prompt_id(prompt_id)
        template = cls.load(prompt_id)
        input_schema = cls._build_default_input_schema_from_template(template)

        raw = {
            "name": name,
            "version": version,
            "description": PROMPT_REGISTRY[prompt_id].get("description"),
            "input_schema": input_schema,
            "template": template,
        }
        return validate_prompt_definition(raw)

    @classmethod
    def get_identity(cls, prompt_id: str):
        defn = cls.get_definition(prompt_id)
        return compute_prompt_identity(defn)
