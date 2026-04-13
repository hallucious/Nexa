from __future__ import annotations

from typing import Any, Callable, Mapping

from src.designer.semantic_backend_presets import (
    build_semantic_backend_from_preset,
    build_semantic_backend_with_session,
)
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
    semantic_backend_session_key: str | None = None,
    semantic_backend_session_keys: Mapping[str, str] | None = None,
    use_llm_semantic_interpreter: bool = False,
    llm_backend_required: bool = False,
) -> DesignerSemanticInterpreter:
    """Build the Stage 1 interpreter for Designer normalization.

    Resolution priority for the semantic backend:
      1. semantic_interpreter — already-built interpreter, used as-is.
      2. semantic_backend — already-built backend object.
      3. session key path (beginner / UI path):
           - semantic_backend_session_key: key for the specific preset.
           - semantic_backend_session_keys: mapping of preset → key (first
             preset with a non-empty key wins).
         These paths do not require env var knowledge.
      4. semantic_backend_preset + use_env_provider — traditional env path.
    """
    if semantic_interpreter is not None:
        return semantic_interpreter

    resolved_backend = semantic_backend

    # Session-key path (beginner / UI): no env var knowledge required.
    if resolved_backend is None and semantic_backend_preset is not None:
        session_key: str | None = semantic_backend_session_key

        # If a multi-preset session map is supplied, look up the active preset.
        if not session_key and semantic_backend_session_keys:
            session_key = (semantic_backend_session_keys.get(semantic_backend_preset) or "").strip() or None

        if session_key:
            try:
                resolved_backend = build_semantic_backend_with_session(
                    semantic_backend_preset,
                    session_key=session_key,
                )
            except Exception:
                resolved_backend = None

    # Env-var / .env path (developer / local-bridge path).
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
