from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Type


class PromptSpecError(ValueError):
    """Raised when a PromptSpec cannot be rendered due to invalid inputs."""


@dataclass(frozen=True)
class PromptSpec:
    """Data-first prompt specification (format-string based, v0.1).

    - template uses Python's str.format(**vars)
    - inputs_schema is a mapping: key -> python type (e.g., str, int)
    """

    id: str
    version: str
    template: str
    inputs_schema: Dict[str, Type[Any]] = field(default_factory=dict)
    policy_tags: Optional[list[str]] = None
    notes: Optional[str] = None

    def validate_inputs(self, inputs: Mapping[str, Any]) -> None:
        # Required keys + type checks
        for key, typ in self.inputs_schema.items():
            if key not in inputs:
                raise PromptSpecError(f"Missing required input: {key}")
            val = inputs[key]
            if not isinstance(val, typ):
                raise PromptSpecError(
                    f"Invalid type for '{key}': expected {getattr(typ, '__name__', str(typ))}, got {type(val).__name__}"
                )

    def render(self, inputs: Mapping[str, Any]) -> str:
        self.validate_inputs(inputs)
        try:
            # Allow extra keys beyond schema.
            return self.template.format(**dict(inputs))
        except KeyError as e:
            # Template references key not provided
            raise PromptSpecError(f"Template missing input: {e}") from e
        except Exception as e:
            raise PromptSpecError(f"Failed to render template: {type(e).__name__}: {e}") from e
