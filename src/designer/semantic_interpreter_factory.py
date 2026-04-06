from __future__ import annotations

from typing import Any, Callable, Mapping

from src.designer.semantic_backend_presets import build_semantic_backend_from_preset
from src.designer.semantic_interpreter import (
    DesignerSemanticInterpreter,
    LLMBackedStructuredSemanticInterpreter,
    LegacyRuleBasedSemanticInterpreter,
    SemanticIntentStructuredBackend,
)


def build_designer_semantic_interpreter(
    *,
    semantic_interpreter: DesignerSemanticInterpreter | None = None,
    semantic_backend: SemanticIntentStructuredBackend | None = None,
    semantic_backend_preset: str | None = None,
    semantic_backend_preset_providers: Mapping[str, Any] | None = None,
    semantic_backend_preset_factories: Mapping[str, Callable[[], Any]] | None = None,
    semantic_backend_preset_use_env: bool = False,
    use_llm_semantic_interpreter: bool = False,
    llm_backend_required: bool = False,
) -> DesignerSemanticInterpreter:
    """Build the Stage 1 interpreter for Designer normalization.

    This centralizes the migration-era selection logic so the compatibility
    facade does not continue to own semantic pipeline construction details.
    """

    if semantic_interpreter is not None:
        return semantic_interpreter

    resolved_backend = semantic_backend
    if resolved_backend is None and semantic_backend_preset is not None:
        resolved_backend = build_semantic_backend_from_preset(
            semantic_backend_preset,
            providers=semantic_backend_preset_providers,
            provider_factories=semantic_backend_preset_factories,
            use_env_provider=semantic_backend_preset_use_env,
        )

    if resolved_backend is not None or use_llm_semantic_interpreter:
        if resolved_backend is None and llm_backend_required:
            raise ValueError("semantic_backend is required when llm_backend_required=True")
        if resolved_backend is None:
            return LegacyRuleBasedSemanticInterpreter()
        return LLMBackedStructuredSemanticInterpreter(
            backend=resolved_backend,
            fallback_interpreter=LegacyRuleBasedSemanticInterpreter(),
            allow_fallback=not llm_backend_required,
        )

    return LegacyRuleBasedSemanticInterpreter()
