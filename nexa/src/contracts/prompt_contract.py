from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptError:
    """
    Prompt rendering error surface.
    """
    type: str
    message: str
    retryable: bool = False


@dataclass
class PromptRenderResult:
    """
    Result of rendering a prompt template with a runtime context.
    """
    prompt_id: str
    version: str
    rendered_text: str
    variables_used: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[PromptError] = None


@dataclass
class PromptTemplate:
    """
    Versioned prompt template contract.

    Rendering mode:
    - Python str.format style
    - Example: "Answer the question: {question}"
    """
    prompt_id: str
    version: str
    template: str
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, context: Dict[str, Any]) -> PromptRenderResult:
        missing = [name for name in self.variables if name not in context]
        if missing:
            return PromptRenderResult(
                prompt_id=self.prompt_id,
                version=self.version,
                rendered_text="",
                variables_used={k: context[k] for k in self.variables if k in context},
                metadata=dict(self.metadata),
                error=PromptError(
                    type="missing_variables",
                    message=f"Missing prompt variables: {', '.join(missing)}",
                    retryable=False,
                ),
            )

        try:
            rendered = self.template.format(**context)
        except KeyError as exc:
            missing_name = str(exc).strip("'")
            return PromptRenderResult(
                prompt_id=self.prompt_id,
                version=self.version,
                rendered_text="",
                variables_used={k: v for k, v in context.items() if k in self.variables},
                metadata=dict(self.metadata),
                error=PromptError(
                    type="missing_variables",
                    message=f"Missing prompt variable: {missing_name}",
                    retryable=False,
                ),
            )
        except Exception as exc:
            return PromptRenderResult(
                prompt_id=self.prompt_id,
                version=self.version,
                rendered_text="",
                variables_used={k: v for k, v in context.items() if k in self.variables},
                metadata=dict(self.metadata),
                error=PromptError(
                    type="render_failure",
                    message=str(exc),
                    retryable=False,
                ),
            )

        return PromptRenderResult(
            prompt_id=self.prompt_id,
            version=self.version,
            rendered_text=rendered,
            variables_used={k: context[k] for k in self.variables if k in context},
            metadata=dict(self.metadata),
            error=None,
        )
