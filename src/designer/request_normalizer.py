from __future__ import annotations

from typing import Any, Callable, Mapping
import hashlib

from src.designer.models.designer_intent import DesignerIntent

from src.designer.legacy_mutation_heuristics import DesignerLegacyMutationHeuristics
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
        use_llm_semantic_interpreter: bool = False,
        llm_backend_required: bool = False,
    ) -> None:
        self._semantic_interpreter = build_designer_semantic_interpreter(
            semantic_interpreter=semantic_interpreter,
            semantic_backend=semantic_backend,
            semantic_backend_preset=semantic_backend_preset,
            semantic_backend_preset_providers=semantic_backend_preset_providers,
            semantic_backend_preset_factories=semantic_backend_preset_factories,
            semantic_backend_preset_use_env=semantic_backend_preset_use_env,
            use_llm_semantic_interpreter=use_llm_semantic_interpreter,
            llm_backend_required=llm_backend_required,
        )
        self._symbolic_grounder = symbolic_grounder or DeterministicSymbolicGrounder()
        self._legacy_heuristics = DesignerLegacyMutationHeuristics(self._symbolic_grounder)
        self._referential_support = DesignerReferentialResolutionSupport(self._legacy_heuristics)
        self._outcome_projector = SemanticGroundingOutcomeProjector()
        self._intent_support = DesignerIntentAssemblySupport(
            self._legacy_heuristics,
            self._referential_support,
        )

    def normalize(self, request_text: str, *, context: RequestNormalizationContext | None = None) -> DesignerIntent:
        if not request_text or not request_text.strip():
            raise ValueError("request_text must be non-empty")
        context = context or RequestNormalizationContext()
        if context.session_state_card is not None and context.working_save_ref is None:
            context = RequestNormalizationContext(
                working_save_ref=context.session_state_card.current_working_save.savefile_ref,
                session_state_card=context.session_state_card,
            )
        semantic_intent = self._semantic_interpreter.interpret(request_text, context=context)
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
