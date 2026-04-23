from __future__ import annotations

from typing import Any, Callable, Mapping
import hashlib

from src.designer.models.designer_intent import DesignerIntent

from src.designer.referential_resolution_support import DesignerReferentialResolutionSupport
from src.designer.intent_assembly_support import DesignerIntentAssemblySupport
from src.designer.normalization_context import RequestNormalizationContext
from src.designer.semantic_grounding_outcome import SemanticGroundingOutcomeProjector
from src.designer.semantic_interpreter import (
    DesignerSemanticInterpreter,
    SemanticIntentStructuredBackend,
)
from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
from src.designer.symbolic_grounder import (
    DesignerSymbolicGrounder,
    DeterministicSymbolicGrounder,
)


class DesignerRequestNormalizer:
    """Compatibility facade for Designer request normalization.

    Stage 1 semantic interpretation and Stage 2 symbolic grounding are now
    modeled as separate subsystems. This facade preserves the existing public
    API while the implementation migrates away from a monolithic normalizer.
    """

    def __init__(
        self,
        *,
        semantic_interpreter: DesignerSemanticInterpreter | None = None,
        symbolic_grounder: DesignerSymbolicGrounder | None = None,
        semantic_backend: SemanticIntentStructuredBackend | None = None,
        semantic_backend_preset: str | None = None,
        semantic_backend_preset_providers: Mapping[str, Any] | None = None,
        semantic_backend_preset_factories: Mapping[str, Callable[[], Any]] | None = None,
        semantic_backend_preset_use_env: bool = False,
        semantic_backend_session_key: str | None = None,
        semantic_backend_session_keys: Mapping[str, str] | None = None,
        use_llm_semantic_interpreter: bool = False,
        llm_backend_required: bool = False,
    ) -> None:
        self._prebuilt_semantic_interpreter = semantic_interpreter
        self._semantic_backend = semantic_backend
        self._semantic_backend_preset = semantic_backend_preset
        self._semantic_backend_preset_providers = semantic_backend_preset_providers
        self._semantic_backend_preset_factories = semantic_backend_preset_factories
        self._semantic_backend_preset_use_env = semantic_backend_preset_use_env
        self._semantic_backend_session_key = (semantic_backend_session_key or "").strip() or None
        self._semantic_backend_session_keys = self._normalize_session_keys(semantic_backend_session_keys)
        self._use_llm_semantic_interpreter = use_llm_semantic_interpreter
        self._llm_backend_required = llm_backend_required
        try:
            self._semantic_interpreter = build_designer_semantic_interpreter(
                semantic_interpreter=semantic_interpreter,
                semantic_backend=semantic_backend,
                semantic_backend_preset=semantic_backend_preset,
                semantic_backend_preset_providers=semantic_backend_preset_providers,
                semantic_backend_preset_factories=semantic_backend_preset_factories,
                semantic_backend_preset_use_env=semantic_backend_preset_use_env,
                semantic_backend_session_key=self._semantic_backend_session_key,
                semantic_backend_session_keys=self._semantic_backend_session_keys,
                use_llm_semantic_interpreter=use_llm_semantic_interpreter,
                llm_backend_required=llm_backend_required,
            )
        except ValueError as exc:
            allow_deferred_session_resolution = (
                semantic_interpreter is None
                and semantic_backend is None
                and semantic_backend_preset is not None
                and not llm_backend_required
                and "No provider configured for semantic backend preset" in str(exc)
            )
            if not allow_deferred_session_resolution:
                raise
            self._semantic_interpreter = build_designer_semantic_interpreter()
        self._symbolic_grounder = symbolic_grounder or DeterministicSymbolicGrounder()
        self._referential_support = DesignerReferentialResolutionSupport(self._symbolic_grounder)
        self._outcome_projector = SemanticGroundingOutcomeProjector()
        self._intent_support = DesignerIntentAssemblySupport(
            self._semantic_interpreter,
            self._symbolic_grounder,
            self._referential_support,
        )

    @staticmethod
    def _normalize_session_keys(session_keys: Mapping[str, str] | None) -> dict[str, str]:
        normalized: dict[str, str] = {}
        if not session_keys:
            return normalized
        for preset, key in session_keys.items():
            if isinstance(preset, str) and isinstance(key, str) and key.strip():
                normalized[preset] = key.strip()
        return normalized

    def _session_keys_from_context(self, context: RequestNormalizationContext | None) -> dict[str, str]:
        if context is None or context.session_state_card is None:
            return {}
        notes = context.session_state_card.notes
        raw = notes.get("provider_session_keys") if isinstance(notes, dict) else None
        if not isinstance(raw, Mapping):
            return {}
        return self._normalize_session_keys(raw)

    def _semantic_interpreter_for_context(
        self,
        context: RequestNormalizationContext | None,
        *,
        semantic_backend_session_key: str | None = None,
        semantic_backend_session_keys: Mapping[str, str] | None = None,
    ) -> DesignerSemanticInterpreter:
        if self._prebuilt_semantic_interpreter is not None:
            return self._prebuilt_semantic_interpreter
        effective_session_key = (semantic_backend_session_key or "").strip() or self._semantic_backend_session_key
        effective_session_keys = dict(self._semantic_backend_session_keys)
        effective_session_keys.update(self._session_keys_from_context(context))
        effective_session_keys.update(self._normalize_session_keys(semantic_backend_session_keys))
        if not effective_session_key and not effective_session_keys:
            return self._semantic_interpreter
        return build_designer_semantic_interpreter(
            semantic_backend=self._semantic_backend,
            semantic_backend_preset=self._semantic_backend_preset,
            semantic_backend_preset_providers=self._semantic_backend_preset_providers,
            semantic_backend_preset_factories=self._semantic_backend_preset_factories,
            semantic_backend_preset_use_env=self._semantic_backend_preset_use_env,
            semantic_backend_session_key=effective_session_key,
            semantic_backend_session_keys=effective_session_keys or None,
            use_llm_semantic_interpreter=self._use_llm_semantic_interpreter,
            llm_backend_required=self._llm_backend_required,
        )

    def normalize(
        self,
        request_text: str,
        *,
        context: RequestNormalizationContext | None = None,
        semantic_backend_session_key: str | None = None,
        semantic_backend_session_keys: Mapping[str, str] | None = None,
    ) -> DesignerIntent:
        if not request_text or not request_text.strip():
            raise ValueError("request_text must be non-empty")
        context = context or RequestNormalizationContext()
        if context.session_state_card is not None and context.working_save_ref is None:
            context = RequestNormalizationContext(
                working_save_ref=context.session_state_card.current_working_save.savefile_ref,
                session_state_card=context.session_state_card,
            )
        semantic_interpreter = self._semantic_interpreter_for_context(
            context,
            semantic_backend_session_key=semantic_backend_session_key,
            semantic_backend_session_keys=semantic_backend_session_keys,
        )
        semantic_intent = semantic_interpreter.interpret(request_text, context=context)
        effective_request_text = semantic_intent.effective_request_text
        category = semantic_intent.category
        scope = self._intent_support.build_scope(category, effective_request_text, context)
        grounded_intent = self._symbolic_grounder.ground(
            semantic_intent,
            context=context,
            precomputed_scope=scope,
        )
        scope = grounded_intent.target_scope
        actions = self._intent_support.build_actions(category, effective_request_text, scope, context, grounded_intent=grounded_intent)
        assumptions = self._intent_support.build_assumptions(category, effective_request_text, context, raw_request_text=request_text)
        assumptions.extend(self._outcome_projector.build_semantic_assumptions(semantic_intent, context=context))
        assumptions.extend(self._outcome_projector.build_grounding_assumptions(grounded_intent, context=context))
        ambiguity_flags = self._intent_support.build_ambiguity_flags(category, effective_request_text, context)
        ambiguity_flags.extend(self._outcome_projector.build_semantic_ambiguity_flags(semantic_intent, context=context))
        ambiguity_flags.extend(self._outcome_projector.build_grounding_ambiguity_flags(grounded_intent))
        risk_flags = self._intent_support.build_risk_flags(effective_request_text, context)
        requires_confirmation = bool(
            semantic_intent.clarification_required or ambiguity_flags or [flag for flag in risk_flags if flag.severity == "high"]
        )
        constraints = self._intent_support.build_constraints(request_text, context)
        objective = self._intent_support.build_objective(request_text, context)
        explanation = self._outcome_projector.build_explanation(category, scope.mode, ambiguity_flags, semantic_intent=semantic_intent, grounded_intent=grounded_intent, context=context)
        return DesignerIntent(
            intent_id=_stable_id("intent", request_text),
            category=category,
            user_request_text=request_text.strip(),
            target_scope=scope,
            objective=objective,
            constraints=constraints,
            proposed_actions=tuple(actions),
            assumptions=tuple(assumptions),
            ambiguity_flags=tuple(ambiguity_flags),
            risk_flags=tuple(risk_flags),
            requires_user_confirmation=requires_confirmation,
            confidence=self._outcome_projector.estimate_confidence(ambiguity_flags, semantic_intent=semantic_intent),
            explanation=explanation,
        )



def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"
