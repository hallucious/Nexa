from __future__ import annotations

from src.designer.models.designer_intent import AmbiguityFlag, AssumptionSpec
from src.designer.normalization_context import RequestNormalizationContext


class SemanticGroundingOutcomeProjector:
    """Project Stage 1/2 outcomes into user-visible Designer intent state.

    This keeps semantic/grounding ambiguity surfacing out of the compatibility
    facade so ``request_normalizer.py`` no longer owns as much post-processing
    behavior directly.
    """

    def build_semantic_assumptions(self, semantic_intent, *, context: RequestNormalizationContext) -> list[AssumptionSpec]:
        assumptions: list[AssumptionSpec] = []
        for note in semantic_intent.semantic_ambiguity_notes:
            assumptions.append(
                AssumptionSpec(
                    text=f"Semantic ambiguity noted by interpreter: {note}",
                    severity="medium",
                    user_visible=True,
                )
            )
        if self._semantic_clarification_loop_persisting(semantic_intent, context):
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "A prior clarification attempt is already present in the session context, "
                        "but the semantic interpreter still requires clarification. Treat this as a persistent clarification loop until the target or action is made more explicit."
                    ),
                    severity="medium",
                    user_visible=True,
                )
            )
        return assumptions

    def build_semantic_ambiguity_flags(self, semantic_intent, *, context: RequestNormalizationContext) -> list[AmbiguityFlag]:
        flags: list[AmbiguityFlag] = []
        if semantic_intent.clarification_required:
            questions_text = (
                "; ".join(semantic_intent.clarification_questions)
                if semantic_intent.clarification_questions
                else "The semantic interpreter requires clarification before deterministic grounding can be trusted."
            )
            flags.append(
                AmbiguityFlag(
                    type="semantic_interpretation_requires_clarification",
                    description=questions_text,
                )
            )
            if self._semantic_clarification_loop_persisting(semantic_intent, context):
                flags.append(
                    AmbiguityFlag(
                        type="semantic_clarification_loop_persisting",
                        description="The user already provided a clarification context, but the semantic interpreter still cannot resolve the request without another clarification pass.",
                    )
                )
        return flags

    def build_grounding_assumptions(self, grounded_intent, *, context: RequestNormalizationContext) -> list[AssumptionSpec]:
        if grounded_intent is None:
            return []
        assumptions: list[AssumptionSpec] = []
        semantic_count = len(grounded_intent.semantic_intent.action_candidates)
        grounded_count = len(grounded_intent.grounded_action_candidates)
        prior_clarification_present = self._semantic_clarification_present(context)
        if semantic_count > grounded_count and grounded_count > 0:
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "Only part of the semantic request could be grounded deterministically. "
                        f"{grounded_count} of {semantic_count} requested action(s) were preserved as concrete mutations; the remaining actions require clarification or better structural anchors."
                    ),
                    severity="medium",
                    user_visible=True,
                )
            )
            if prior_clarification_present:
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "A prior clarification improved the current semantic request, but only part of it could be grounded deterministically. "
                            f"{grounded_count} of {semantic_count} requested action(s) are now concrete; the remaining actions still require clarification or better structural anchors."
                        ),
                        severity="medium",
                        user_visible=True,
                    )
                )
        if (
            prior_clarification_present
            and semantic_count > 0
            and grounded_count == semantic_count
            and not grounded_intent.semantic_intent.clarification_required
            and not grounded_intent.grounding_notes
        ):
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "A prior clarification resolved the current semantic request into fully grounded concrete actions. "
                        f"All {grounded_count} requested action(s) are now grounded deterministically."
                    ),
                    severity="low",
                    user_visible=True,
                )
            )
        return assumptions

    def build_grounding_ambiguity_flags(self, grounded_intent) -> list[AmbiguityFlag]:
        if grounded_intent is None:
            return []
        flags: list[AmbiguityFlag] = []
        semantic_count = len(grounded_intent.semantic_intent.action_candidates)
        grounded_count = len(grounded_intent.grounded_action_candidates)
        if semantic_count > grounded_count and grounded_count > 0:
            flags.append(
                AmbiguityFlag(
                    type="semantic_grounding_partial_resolution",
                    description=(
                        "Some semantic actions were grounded successfully, but at least one action remained unresolved. "
                        f"Grounded {grounded_count} of {semantic_count} requested actions."
                    ),
                )
            )
        for note in grounded_intent.grounding_notes:
            if note.startswith("grounding_ambiguous_target:"):
                flags.append(
                    AmbiguityFlag(
                        type="semantic_grounding_target_ambiguous",
                        description="The semantic action matched multiple plausible node targets and requires confirmation before a deterministic mutation can be generated.",
                    )
                )
            elif note == "grounding_unresolved_target:missing":
                flags.append(
                    AmbiguityFlag(
                        type="semantic_grounding_target_unresolved",
                        description="The semantic action could not be grounded to a unique node target.",
                    )
                )
            elif note.startswith("grounding_unresolved_resource:"):
                _, action_type, resource_kind = note.split(":", 2)
                flags.append(
                    AmbiguityFlag(
                        type="semantic_grounding_resource_unresolved",
                        description=f"The semantic action '{action_type}' could not be grounded to an available {resource_kind} resource.",
                    )
                )
            elif note == "grounding_unresolved_topology:insert_node_between":
                flags.append(
                    AmbiguityFlag(
                        type="semantic_grounding_topology_unresolved",
                        description="The semantic insert action could not be grounded to a unique topology placement.",
                    )
                )
        return flags

    def build_explanation(
        self,
        category: str,
        scope_mode: str,
        ambiguity_flags: list[AmbiguityFlag],
        *,
        semantic_intent,
        grounded_intent,
        context: RequestNormalizationContext,
    ) -> str:
        message = f"Normalized request into {category} with target scope mode '{scope_mode}'."
        flag_types = {flag.type for flag in ambiguity_flags}
        if semantic_intent.clarification_required and semantic_intent.clarification_questions:
            message += " Clarification needed: " + "; ".join(semantic_intent.clarification_questions)
            if "semantic_clarification_loop_persisting" in flag_types:
                message += " A prior clarification is already present, so this request remains in a clarification loop until the target or action is made more explicit."
        elif ambiguity_flags:
            message += " User confirmation is required before any commit boundary is crossed."
        recovery_state = self._grounding_recovery_state(grounded_intent, context)
        if recovery_state == "fully_resolved_after_clarification":
            message += " A prior clarification resolved the request into concrete grounded actions."
        elif recovery_state == "partially_resolved_after_clarification":
            message += " A prior clarification resolved part of the request, but some actions remain unresolved."
        if "semantic_grounding_partial_resolution" in flag_types:
            message += " Some requested actions were grounded successfully, but at least one action remains unresolved."
        return message

    def estimate_confidence(self, ambiguity_flags: list[AmbiguityFlag], *, semantic_intent) -> float:
        base = 0.65 if ambiguity_flags else 0.9
        if semantic_intent.clarification_required:
            base = min(base, 0.45)
        return min(base, semantic_intent.confidence_hint)

    def _semantic_clarification_present(self, context: RequestNormalizationContext) -> bool:
        card = context.session_state_card
        if card is None:
            return False
        if card.conversation_context.clarified_interpretation:
            return True
        return bool(card.revision_state.user_corrections)

    def _grounding_recovery_state(self, grounded_intent, context: RequestNormalizationContext) -> str | None:
        if grounded_intent is None or not self._semantic_clarification_present(context):
            return None
        semantic_count = len(grounded_intent.semantic_intent.action_candidates)
        grounded_count = len(grounded_intent.grounded_action_candidates)
        if semantic_count == 0:
            return None
        if grounded_count == semantic_count and not grounded_intent.semantic_intent.clarification_required and not grounded_intent.grounding_notes:
            return "fully_resolved_after_clarification"
        if grounded_count > 0 and grounded_count < semantic_count:
            return "partially_resolved_after_clarification"
        return None

    def _semantic_clarification_loop_persisting(self, semantic_intent, context: RequestNormalizationContext) -> bool:
        if not semantic_intent.clarification_required:
            return False
        return self._semantic_clarification_present(context)
