from __future__ import annotations

import re
from typing import Any, Dict, Tuple

from .prompt_schema import PromptDefinition, validate_render_input
from .store import PromptStore


class PromptRenderer:
    """Render {{placeholders}} in prompt templates.

    - Versioned prompt_id is mandatory for strict rendering.
    - Before templating, validate_render_input() is called using prompt-declared input_schema.
    """

    PLACEHOLDER_PATTERN = re.compile(r"{{\s*(\w+)\s*}}")

    @classmethod
    def _validate_all_placeholders_have_values(cls, template: str, kwargs: Dict[str, Any]) -> None:
        placeholders = set(cls.PLACEHOLDER_PATTERN.findall(template))
        missing = sorted([ph for ph in placeholders if ph not in kwargs])
        if missing:
            raise ValueError(f"Template placeholders have no values: {missing}")

    @classmethod
    def render(cls, template: str, **kwargs: Any) -> str:
        # Backward compatible rendering for legacy call-sites.
        cls._validate_all_placeholders_have_values(template, kwargs)
        result = template
        for k, v in kwargs.items():
            result = re.sub(r"{{\s*" + re.escape(k) + r"\s*}}", str(v), result)
        return result

    @classmethod
    def render_definition(cls, defn: PromptDefinition, variables: Dict[str, Any]) -> str:
        validate_render_input(defn, variables)
        cls._validate_all_placeholders_have_values(defn.template, variables)
        return cls.render(defn.template, **variables)

    @classmethod
    def render_prompt(cls, prompt_id: str, **variables: Any) -> Tuple[str, Any]:
        """Strict path: load PromptDefinition by id, validate inputs, render, and return (text, identity)."""
        defn = PromptStore.get_definition(prompt_id)
        identity = PromptStore.get_identity(prompt_id)
        text = cls.render_definition(defn, variables)
        return text, identity
