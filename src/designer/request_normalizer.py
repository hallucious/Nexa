from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from src.designer.models.designer_intent import (
    ActionSpec,
    AmbiguityFlag,
    AssumptionSpec,
    ConstraintSet,
    DesignerIntent,
    ObjectiveSpec,
    RiskFlag,
    TargetScope,
)


from src.designer.models.designer_session_state_card import DesignerSessionStateCard

@dataclass(frozen=True)
class RequestNormalizationContext:
    working_save_ref: str | None = None
    session_state_card: DesignerSessionStateCard | None = None


class DesignerRequestNormalizer:
    """Rule-based Step 2 request normalizer.

    This intentionally avoids LLM calls and produces bounded, reviewable intent
    objects for mutation-oriented designer requests.
    """

    def normalize(self, request_text: str, *, context: RequestNormalizationContext | None = None) -> DesignerIntent:
        if not request_text or not request_text.strip():
            raise ValueError("request_text must be non-empty")
        context = context or RequestNormalizationContext()
        if context.session_state_card is not None and context.working_save_ref is None:
            context = RequestNormalizationContext(
                working_save_ref=context.session_state_card.current_working_save.savefile_ref,
                session_state_card=context.session_state_card,
            )
        effective_request_text = self._compose_effective_request_text(request_text, context)
        category = self._infer_category(effective_request_text)
        scope = self._build_scope(category, effective_request_text, context)
        actions = self._build_actions(category, effective_request_text)
        assumptions = self._build_assumptions(category, effective_request_text, context)
        ambiguity_flags = self._build_ambiguity_flags(category, effective_request_text, context)
        risk_flags = self._build_risk_flags(effective_request_text)
        requires_confirmation = bool(ambiguity_flags or [flag for flag in risk_flags if flag.severity == "high"])
        constraints = self._build_constraints(request_text, context)
        objective = self._build_objective(request_text, context)
        explanation = self._build_explanation(category, scope, ambiguity_flags)
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
            confidence=self._estimate_confidence(ambiguity_flags),
            explanation=explanation,
        )


    def _compose_effective_request_text(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> str:
        card = context.session_state_card
        if card is None:
            return request_text
        parts = [request_text.strip()]
        if card.conversation_context.clarified_interpretation:
            parts.append(card.conversation_context.clarified_interpretation.strip())
        if card.revision_state.user_corrections:
            parts.extend(item.strip() for item in card.revision_state.user_corrections if item.strip())
        return " ".join(part for part in parts if part)

    def _infer_category(self, request_text: str) -> str:
        text = request_text.casefold()
        if any(term in text for term in ("explain", "what does", "why is this")):
            return "EXPLAIN_CIRCUIT"
        if any(term in text for term in ("repair", "fix", "broken", "restore")):
            return "REPAIR_CIRCUIT"
        if any(term in text for term in ("optimize", "optimise", "improve", "reduce cost", "more reliable")):
            return "OPTIMIZE_CIRCUIT"
        if any(term in text for term in ("analyze", "analyse", "risk", "cost", "gap", "why might")):
            return "ANALYZE_CIRCUIT"
        if any(term in text for term in ("create", "make", "build", "new circuit")):
            return "CREATE_CIRCUIT"
        if any(term in text for term in ("add", "change", "replace", "remove", "rename", "insert", "update")):
            return "MODIFY_CIRCUIT"
        return "MODIFY_CIRCUIT"

    def _build_scope(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> TargetScope:
        text = request_text.casefold()
        broad = any(term in text for term in ("all ", "entire", "whole", "across the circuit", "every"))
        node_refs = self._resolve_node_refs(self._extract_node_refs(request_text), context)
        max_change_scope = "broad" if broad else "bounded"
        card_scope = context.session_state_card.target_scope if context.session_state_card is not None else None
        if category == "CREATE_CIRCUIT":
            mode = card_scope.mode if card_scope is not None and card_scope.mode == "new_circuit" else "new_circuit"
            max_scope = card_scope.touch_budget if card_scope is not None else max_change_scope
            return TargetScope(mode=mode, node_refs=node_refs, max_change_scope=max_scope)
        if category in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"}:
            return TargetScope(
                mode="read_only",
                savefile_ref=context.working_save_ref,
                node_refs=node_refs,
                max_change_scope="minimal",
            )
        if card_scope is not None:
            if card_scope.mode == "node_only":
                refs = tuple(node_refs) or tuple(card_scope.allowed_node_refs)
                return TargetScope(
                    mode="node_only",
                    savefile_ref=context.working_save_ref,
                    node_refs=refs,
                    max_change_scope=card_scope.touch_budget,
                )
            if node_refs:
                return TargetScope(
                    mode="node_only",
                    savefile_ref=context.working_save_ref,
                    node_refs=node_refs,
                    max_change_scope=card_scope.touch_budget,
                )
            return TargetScope(
                mode=card_scope.mode if card_scope.mode != "read_only" else "existing_circuit",
                savefile_ref=context.working_save_ref,
                node_refs=tuple(card_scope.allowed_node_refs),
                edge_refs=tuple(card_scope.allowed_edge_refs),
                max_change_scope=card_scope.touch_budget,
            )
        if node_refs:
            return TargetScope(
                mode="node_only",
                savefile_ref=context.working_save_ref,
                node_refs=node_refs,
                max_change_scope=max_change_scope,
            )
        return TargetScope(
            mode="existing_circuit",
            savefile_ref=context.working_save_ref,
            max_change_scope=max_change_scope,
        )

    def _build_constraints(self, request_text: str, context: RequestNormalizationContext) -> ConstraintSet:
        text = request_text.casefold()
        base = ConstraintSet(
            cost_limit="low" if "low cost" in text or "reduce cost" in text else None,
            speed_priority="high" if "faster" in text or "latency" in text else None,
            quality_priority="high" if "quality" in text or "reliable" in text else None,
            determinism_preference="high" if "determin" in text else None,
            human_review_required="review" in text or "approve" in text,
        )
        card = context.session_state_card
        if card is None:
            return base
        return ConstraintSet(
            cost_limit=base.cost_limit or card.constraints.cost_limit,
            speed_priority=base.speed_priority or card.constraints.speed_priority,
            quality_priority=base.quality_priority or card.constraints.quality_priority,
            determinism_preference=base.determinism_preference or card.constraints.determinism_preference,
            provider_preferences=card.constraints.provider_preferences,
            provider_restrictions=card.constraints.provider_restrictions,
            plugin_preferences=card.constraints.plugin_preferences,
            plugin_restrictions=card.constraints.plugin_restrictions,
            human_review_required=base.human_review_required or card.constraints.human_review_required,
            safety_level=card.constraints.safety_level,
            output_requirements=card.constraints.output_requirements,
            forbidden_patterns=card.constraints.forbidden_patterns,
        )

    def _build_objective(self, request_text: str, context: RequestNormalizationContext) -> ObjectiveSpec:
        card = context.session_state_card
        if card is None:
            return ObjectiveSpec(primary_goal=request_text.strip())
        return ObjectiveSpec(
            primary_goal=request_text.strip(),
            secondary_goals=card.objective.secondary_goals,
            success_criteria=card.objective.success_criteria,
            preferred_behavior=card.objective.preferred_behavior,
        )

    def _build_actions(self, category: str, request_text: str) -> list[ActionSpec]:
        text = request_text.casefold()
        if category == "CREATE_CIRCUIT":
            return [
                ActionSpec(
                    action_type="create_node",
                    target_ref="node.start",
                    parameters={"kind": "provider"},
                    rationale="A new circuit proposal requires at least one starting node.",
                ),
                ActionSpec(
                    action_type="define_output",
                    target_ref="output.final",
                    parameters={"source": "node.start.output"},
                    rationale="A new circuit proposal should expose an explicit output binding.",
                ),
            ]
        actions: list[ActionSpec] = []
        if any(term in text for term in ("review", "approve", "human review")):
            actions.append(
                ActionSpec(
                    action_type="add_review_gate",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"review_type": "manual"},
                    rationale="The request explicitly asks for a review/approval step.",
                )
            )
        if any(term in text for term in ("replace provider", "switch provider", "change provider")):
            provider_id = self._infer_provider_id(text)
            actions.append(
                ActionSpec(
                    action_type="replace_provider",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"provider_id": provider_id},
                    rationale="The request explicitly changes the node provider.",
                )
            )
        if any(term in text for term in ("attach plugin", "add plugin", "use plugin")):
            actions.append(
                ActionSpec(
                    action_type="attach_plugin",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"plugin_id": self._infer_plugin_id(text)},
                    rationale="The request explicitly introduces a plugin-backed tool step.",
                )
            )
        if any(term in text for term in ("rename",)):
            actions.append(
                ActionSpec(
                    action_type="rename_component",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"new_name": "renamed_component"},
                    rationale="The request explicitly asks for a rename operation.",
                )
            )
        if any(term in text for term in ("remove", "delete")):
            actions.append(
                ActionSpec(
                    action_type="delete_node",
                    target_ref=self._first_node_ref(request_text),
                    parameters={},
                    rationale="The request explicitly removes an existing structural element.",
                )
            )
        if any(term in text for term in ("insert", "between")):
            actions.append(
                ActionSpec(
                    action_type="insert_node_between",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"position": "between"},
                    rationale="The request explicitly inserts a node into an existing path.",
                )
            )
        if any(term in text for term in ("change", "update", "modify")) and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"mode": "bounded_update"},
                    rationale="The request asks for a bounded change to existing structure.",
                )
            )
        if category == "REPAIR_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"repair_mode": "minimal_fix"},
                    rationale="Repair requests need a minimal corrective patch proposal.",
                )
            )
        if category == "OPTIMIZE_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="set_parameter",
                    target_ref=self._first_node_ref(request_text),
                    parameters={"optimization_goal": "cost_or_quality"},
                    rationale="Optimization requests are normalized into bounded parameter changes first.",
                )
            )
        return actions

    def _build_assumptions(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> list[AssumptionSpec]:
        assumptions: list[AssumptionSpec] = []
        if category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"} and context.working_save_ref is None:
            assumptions.append(
                AssumptionSpec(
                    text="The current working draft is the intended mutation target.",
                    severity="medium",
                    user_visible=True,
                )
            )
        if "review" in request_text.casefold():
            assumptions.append(
                AssumptionSpec(
                    text="A human reviewer will be available when the review step is reached.",
                    severity="medium",
                    user_visible=True,
                )
            )
        return assumptions

    def _build_ambiguity_flags(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> list[AmbiguityFlag]:
        flags: list[AmbiguityFlag] = []
        text = request_text.casefold()
        if category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"} and context.working_save_ref is None:
            flags.append(
                AmbiguityFlag(
                    type="target_not_explicit",
                    description="The request does not identify which working save should be mutated.",
                )
            )
        has_clarification = bool(
            context.session_state_card is not None
            and context.session_state_card.conversation_context.clarified_interpretation
        )
        if any(term in text for term in ("all ", "entire", "whole")) and not has_clarification:
            flags.append(
                AmbiguityFlag(
                    type="broad_scope",
                    description="The request implies broad-scope changes that should be confirmed before commit.",
                )
            )
        return flags

    def _build_risk_flags(self, request_text: str) -> list[RiskFlag]:
        flags: list[RiskFlag] = []
        text = request_text.casefold()
        if any(term in text for term in ("delete", "remove", "destructive")):
            flags.append(
                RiskFlag(
                    type="destructive_edit",
                    severity="high",
                    description="The request includes destructive structural edits.",
                )
            )
        if "provider" in text and any(term in text for term in ("replace", "switch", "change")):
            flags.append(
                RiskFlag(
                    type="provider_change",
                    severity="medium",
                    description="Provider changes may alter output semantics and cost.",
                )
            )
        return flags

    def _build_explanation(self, category: str, scope: TargetScope, ambiguity_flags: list[AmbiguityFlag]) -> str:
        message = f"Normalized request into {category} with target scope mode '{scope.mode}'."
        if ambiguity_flags:
            message += " User confirmation is required before any commit boundary is crossed."
        return message

    def _estimate_confidence(self, ambiguity_flags: list[AmbiguityFlag]) -> float:
        return 0.65 if ambiguity_flags else 0.9

    def _infer_provider_id(self, text: str) -> str:
        if "claude" in text or "anthropic" in text:
            return "anthropic:claude"
        if "gemini" in text or "google" in text:
            return "google:gemini"
        if "perplexity" in text:
            return "perplexity:sonar"
        return "openai:gpt"

    def _infer_plugin_id(self, text: str) -> str:
        if "search" in text:
            return "web.search"
        if "normalize" in text:
            return "text.normalize"
        if "validate" in text:
            return "schema.validate"
        return "tool.generic"


    def _resolve_node_refs(
        self,
        node_refs: tuple[str, ...],
        context: RequestNormalizationContext,
    ) -> tuple[str, ...]:
        if not node_refs:
            return node_refs
        candidates: tuple[str, ...] = ()
        if context.session_state_card is not None:
            candidates = tuple(context.session_state_card.current_working_save.node_list)
            if not candidates:
                candidates = tuple(context.session_state_card.target_scope.allowed_node_refs)
        if not candidates:
            return node_refs
        resolved: list[str] = []
        for ref in node_refs:
            if ref in candidates:
                resolved.append(ref)
                continue
            suffix_matches = [item for item in candidates if item.endswith(f".{ref}")]
            if len(suffix_matches) == 1:
                resolved.append(suffix_matches[0])
            else:
                resolved.append(ref)
        return tuple(dict.fromkeys(resolved))

    def _extract_node_refs(self, request_text: str) -> tuple[str, ...]:
        prioritized_patterns = (
            r"\bin\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bon\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bfor\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bat\s+node\s+([A-Za-z0-9_\-\.]+)",
            r"\bnode\s+([A-Za-z0-9_\-\.]+)",
        )
        stopwords = {"before", "after", "between", "final", "a", "an", "the"}
        ordered_refs: list[str] = []
        seen: set[str] = set()
        for pattern in prioritized_patterns:
            for match in re.finditer(pattern, request_text, flags=re.IGNORECASE):
                ref = match.group(1).rstrip('.,;:')
                if ref.casefold() in stopwords:
                    continue
                if ref not in seen:
                    ordered_refs.append(ref)
                    seen.add(ref)
        return tuple(ordered_refs)

    def _first_node_ref(self, request_text: str) -> str | None:
        refs = self._extract_node_refs(request_text)
        return refs[0] if refs else None


def _stable_id(prefix: str, raw: str) -> str:
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"
