import re
from .registry import PROMPT_REGISTRY


class PromptRenderer:
    """Render {{placeholders}} in prompt templates.

    Backward compatible with prior signature:
      render(template, **kwargs) -> str

    New optional strict path:
      render_with_id(prompt_id, template, **kwargs) -> str
      - validates required placeholders declared in registry
      - validates that all placeholders in template have values
    """

    PLACEHOLDER_PATTERN = re.compile(r"{{\s*(\w+)\s*}}")

    @classmethod
    def _validate_all_placeholders_have_values(cls, template: str, kwargs):
        placeholders = set(cls.PLACEHOLDER_PATTERN.findall(template))
        missing = sorted([ph for ph in placeholders if ph not in kwargs])
        if missing:
            raise ValueError(f"Template placeholders have no values: {missing}")

    @classmethod
    def render(cls, template: str, **kwargs) -> str:
        # Keep prior behavior but add safety: fail if template contains placeholders without values.
        cls._validate_all_placeholders_have_values(template, kwargs)

        result = template
        for k, v in kwargs.items():
            # Support both {{k}} and {{ k }} forms via regex replace
            result = re.sub(r"{{\s*" + re.escape(k) + r"\s*}}", str(v), result)
        return result

    @classmethod
    def render_with_id(cls, prompt_id: str, template: str, **kwargs) -> str:
        if prompt_id not in PROMPT_REGISTRY:
            raise ValueError(f"Unknown prompt id: {prompt_id}")

        required = PROMPT_REGISTRY[prompt_id].get("required", [])
        missing_required = sorted([k for k in required if k not in kwargs])
        if missing_required:
            raise ValueError(f"Missing required placeholders for {prompt_id}: {missing_required}")

        cls._validate_all_placeholders_have_values(template, kwargs)

        return cls.render(template, **kwargs)
