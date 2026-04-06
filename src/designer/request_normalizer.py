from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import hashlib
import re

from src.designer.control_governance import governance_pending_anchor_snapshot_from_notes, requires_explicit_referential_anchor
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
from src.designer.reason_codes import (
    flag_type_for_reason_code,
    reason_code_for_mixed_referential_request,
)

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
        actions = self._build_actions(category, effective_request_text, scope, context)
        assumptions = self._build_assumptions(category, effective_request_text, context)
        ambiguity_flags = self._build_ambiguity_flags(category, effective_request_text, context)
        risk_flags = self._build_risk_flags(effective_request_text, context)
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
        explicit_node_refs = self._resolve_node_refs(self._extract_node_refs(request_text), context)
        node_refs = self._resolve_target_node_refs_from_committed_summary(
            category,
            request_text,
            context,
            explicit_node_refs,
        )
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

    def _build_actions(
        self,
        category: str,
        request_text: str,
        scope: TargetScope,
        context: RequestNormalizationContext,
    ) -> list[ActionSpec]:
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
        if self._is_confirmation_bounded_mixed_referential_request(request_text):
            return actions
        referential_action = self._resolve_referential_action_resolution(request_text, scope, context)
        if referential_action is not None:
            actions.append(referential_action)
        if any(term in text for term in ("review", "approve", "human review")):
            actions.append(
                ActionSpec(
                    action_type="add_review_gate",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"review_type": "manual"},
                    rationale="The request explicitly asks for a review/approval step.",
                )
            )
        if any(term in text for term in ("replace provider", "switch provider", "change provider")):
            provider_id = self._infer_provider_id(text)
            actions.append(
                ActionSpec(
                    action_type="replace_provider",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"provider_id": provider_id},
                    rationale="The request explicitly changes the node provider.",
                )
            )
        if any(term in text for term in ("attach plugin", "add plugin", "use plugin")):
            actions.append(
                ActionSpec(
                    action_type="attach_plugin",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"plugin_id": self._infer_plugin_id(text)},
                    rationale="The request explicitly introduces a plugin-backed tool step.",
                )
            )
        if any(term in text for term in ("rename",)):
            actions.append(
                ActionSpec(
                    action_type="rename_component",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"new_name": "renamed_component"},
                    rationale="The request explicitly asks for a rename operation.",
                )
            )
        if any(term in text for term in ("remove", "delete")):
            actions.append(
                ActionSpec(
                    action_type="delete_node",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={},
                    rationale="The request explicitly removes an existing structural element.",
                )
            )
        if any(term in text for term in ("insert", "between")):
            actions.append(
                ActionSpec(
                    action_type="insert_node_between",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"position": "between"},
                    rationale="The request explicitly inserts a node into an existing path.",
                )
            )
        if any(term in text for term in ("change", "update", "modify")) and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"mode": "bounded_update"},
                    rationale="The request asks for a bounded change to existing structure.",
                )
            )
        if category == "REPAIR_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"repair_mode": "minimal_fix"},
                    rationale="Repair requests need a minimal corrective patch proposal.",
                )
            )
        if category == "OPTIMIZE_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="set_parameter",
                    target_ref=self._first_target_ref(scope, request_text),
                    parameters={"optimization_goal": "cost_or_quality"},
                    rationale="Optimization requests are normalized into bounded parameter changes first.",
                )
            )
        return actions

    def _resolve_referential_action_resolution(
        self,
        request_text: str,
        scope: TargetScope,
        context: RequestNormalizationContext,
    ) -> ActionSpec | None:
        if not self._uses_safe_revert_action_language(request_text):
            return None
        if self._uses_conflicting_nonrevert_action_language(request_text):
            return None
        summary, _, unresolved_reason = self._resolve_committed_summary_reference(request_text, context)
        if summary is None or unresolved_reason is not None:
            return None
        if self._repeated_cycle_referential_anchor_required(request_text, context, resolved_summary=summary):
            return None
        target_ref = scope.node_refs[0] if len(scope.node_refs) == 1 else None
        touched_node_ids = self._committed_summary_touched_node_ids(summary, context)
        if target_ref is None and len(touched_node_ids) == 1:
            target_ref = touched_node_ids[0]
        if target_ref is None and len(touched_node_ids) != 0:
            return None
        parameters = {
            "operation_mode": "revert_committed_change",
            "commit_id": summary.get("commit_id"),
            "patch_ref": summary.get("patch_ref"),
            "revert_scope": "target_only" if target_ref is not None else "summary_scope",
        }
        return ActionSpec(
            action_type="update_node",
            target_ref=target_ref,
            parameters=parameters,
            rationale="The request explicitly asks to revert or roll back a resolved committed change.",
        )

    def _uses_safe_revert_action_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        return bool(re.search(r"\b(revert|undo|rollback|roll back)\b", text))

    def _uses_conflicting_nonrevert_action_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\b(replace|switch|change) provider\b",
            r"\battach plugin\b",
            r"\badd plugin\b",
            r"\buse plugin\b",
            r"\brename\b",
            r"\binsert\b",
            r"\badd review\b",
            r"\bremove review\b",
            r"\boptimi[sz]e\b",
            r"\brepair\b",
            r"\band\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def _is_confirmation_bounded_mixed_referential_request(self, request_text: str) -> bool:
        return (
            self._uses_referential_committed_summary_language(request_text)
            and self._uses_safe_revert_action_language(request_text)
            and self._uses_conflicting_nonrevert_action_language(request_text)
        )

    def _mixed_referential_action_reason_code(self, request_text: str) -> str:
        return reason_code_for_mixed_referential_request(request_text)

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
        resolved_summary, resolution_mode, unresolved_reason = self._resolve_committed_summary_reference(
            request_text,
            context,
        )
        if resolved_summary is not None:
            if resolution_mode == "latest_auto":
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "Referential continuation language is auto-resolved against the latest committed summary "
                            f"(commit {resolved_summary.get('commit_id', 'unknown')})."
                        ),
                        severity="medium",
                        user_visible=True,
                    )
                )
            elif resolution_mode == "second_latest_auto":
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "Referential continuation language is interpreted against the committed summary before the latest one "
                            f"(commit {resolved_summary.get('commit_id', 'unknown')})."
                        ),
                        severity="medium",
                        user_visible=True,
                    )
                )
            elif resolution_mode == "exact_commit_match":
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "The request explicitly matches committed summary "
                            f"{resolved_summary.get('commit_id', 'unknown')} and is resolved directly against that commit."
                        ),
                        severity="low",
                        user_visible=True,
                    )
                )
            touched_node_ids = self._committed_summary_touched_node_ids(resolved_summary, context)
            explicit_node_refs = self._resolve_node_refs(self._extract_node_refs(request_text), context)
            if not explicit_node_refs and len(touched_node_ids) == 1:
                assumptions.append(
                    AssumptionSpec(
                        text=f"The patch target is auto-resolved to {touched_node_ids[0]} because the referenced committed summary touched exactly one node.",
                        severity="low",
                        user_visible=True,
                    )
                )
            if self._uses_safe_revert_action_language(request_text) and not self._uses_conflicting_nonrevert_action_language(request_text):
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "Safe referential revert language is normalized into a bounded revert_committed_change action "
                            f"against commit {resolved_summary.get('commit_id', 'unknown')}."
                        ),
                        severity="low",
                        user_visible=True,
                    )
                )
            elif self._is_confirmation_bounded_mixed_referential_request(request_text):
                reason_code = self._mixed_referential_action_reason_code(request_text)
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "Mixed referential action language is kept confirmation-bounded instead of being auto-expanded "
                            f"(reason_code={reason_code})."
                        ),
                        severity="medium",
                        user_visible=True,
                    )
                )
        elif unresolved_reason == "missing":
            assumptions.append(
                AssumptionSpec(
                    text="No committed summary is currently available, so referential post-commit language cannot be resolved automatically.",
                    severity="medium",
                    user_visible=True,
                )
            )
        if self._repeated_cycle_referential_anchor_required(request_text, context, resolved_summary=resolved_summary):
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "Repeated confirmation cycles are active for referential interpretation, so auto-resolution is paused until the request includes an explicit commit anchor, explicit node target, or explicit non-latest selector."
                    ),
                    severity="medium",
                    user_visible=True,
                )
            )
            pending_anchor = self._pending_anchor_snapshot_for_request(request_text, context)
            if pending_anchor:
                summary = str(pending_anchor.get("pressure_summary", "")).strip()
                next_actions = pending_anchor.get("next_actions", [])
                detail = summary
                if next_actions:
                    pretty = ", then ".join(str(item).replace("_", " ") for item in next_actions)
                    detail = f"{detail} Next safe step: {pretty}.".strip()
                assumptions.append(
                    AssumptionSpec(
                        text=(
                            "The previous revision cycle already ended under governance anchor pressure, so the next risky referential request should follow the persisted revision guidance. "
                            f"{detail}".strip()
                        ),
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
        _, resolution_mode, unresolved_reason = self._resolve_committed_summary_reference(
            request_text,
            context,
        )
        if unresolved_reason == "missing":
            flags.append(
                AmbiguityFlag(
                    type="committed_summary_missing",
                    description="This request refers to prior committed changes, but no committed summary is available to resolve it.",
                )
            )
        elif unresolved_reason == "insufficient_history":
            flags.append(
                AmbiguityFlag(
                    type="committed_summary_insufficient_history",
                    description="This request refers to an older committed change, but retained committed-summary history is not deep enough to resolve it.",
                )
            )
        elif unresolved_reason == "clarification_required":
            flags.append(
                AmbiguityFlag(
                    type="committed_summary_reference_needs_clarification",
                    description="This request refers to a non-latest committed change without a precise anchor, so clarification is required before automatic resolution.",
                )
            )
        elif resolution_mode == "latest_auto" and self._uses_referential_committed_summary_language(request_text):
            history = self._committed_summary_history(context)
            if len(history) > 1 and (
                self._uses_ambiguous_nonlatest_reference_language(request_text)
                or self._uses_previous_reference_language(request_text)
            ):
                flags.append(
                    AmbiguityFlag(
                        type="committed_summary_reference_history",
                        description="Recent committed history exists, but the request leaves open whether a non-latest summary was intended.",
                    )
                )
        resolved_summary, _, _ = self._resolve_committed_summary_reference(request_text, context)
        if self._repeated_cycle_referential_anchor_required(request_text, context, resolved_summary=resolved_summary):
            pending_anchor = self._pending_anchor_snapshot_for_request(request_text, context)
            suffix = ""
            if pending_anchor:
                pressure_summary = str(pending_anchor.get("pressure_summary", "")).strip()
                if pressure_summary:
                    suffix = f" {pressure_summary}"
            flags.append(
                AmbiguityFlag(
                    type="committed_summary_repeat_cycle_anchor_required",
                    description=(
                        "Recent confirmation cycles repeated the same referential interpretation pattern, so an explicit commit anchor, explicit node target, or explicit non-latest selector is now required before auto-resolution."
                        f"{suffix}"
                    ),
                )
            )

        if resolved_summary is not None and category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"}:
            if self._is_confirmation_bounded_mixed_referential_request(request_text):
                reason_code = self._mixed_referential_action_reason_code(request_text)
                flags.append(
                    AmbiguityFlag(
                        type="committed_summary_action_needs_clarification",
                        description=(
                            "The request combines revert/rollback language with another modification action, so automatic action resolution must be confirmed "
                            f"(reason_code={reason_code})."
                        ),
                    )
                )
                flags.append(
                    AmbiguityFlag(
                        type=flag_type_for_reason_code(reason_code),
                        description=(
                            "This request mixes referential rollback language with another structural action pattern and therefore must remain confirmation-bounded."
                        ),
                    )
                )
            touched_node_ids = self._committed_summary_touched_node_ids(resolved_summary, context)
            explicit_node_refs = self._resolve_node_refs(self._extract_node_refs(request_text), context)
            if explicit_node_refs:
                conflicting = [ref for ref in explicit_node_refs if ref not in touched_node_ids]
                if touched_node_ids and conflicting:
                    flags.append(
                        AmbiguityFlag(
                            type="committed_summary_target_conflict",
                            description="The explicit node target conflicts with the node(s) touched by the referenced committed summary.",
                        )
                    )
            elif self._uses_referential_committed_summary_language(request_text):
                if len(touched_node_ids) > 1:
                    flags.append(
                        AmbiguityFlag(
                            type="committed_summary_target_needs_clarification",
                            description="The referenced committed summary touched multiple nodes, so the patch target must be confirmed.",
                        )
                    )
                elif len(touched_node_ids) == 0:
                    flags.append(
                        AmbiguityFlag(
                            type="committed_summary_target_missing",
                            description="The referenced committed summary does not expose a unique touched node target for automatic patch selection.",
                        )
                    )
        return flags

    def _build_risk_flags(self, request_text: str, context: RequestNormalizationContext) -> list[RiskFlag]:
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
        pending_anchor = self._pending_anchor_snapshot_for_request(request_text, context)
        if pending_anchor:
            summary = str(pending_anchor.get("pressure_summary", "")).strip()
            flags.append(
                RiskFlag(
                    type="governance_pressure_carryover",
                    severity="medium",
                    description=(
                        "This request re-enters a referential interpretation path while prior governance pressure remains unresolved."
                        + (f" {summary}" if summary else "")
                    ),
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

    def _repeated_cycle_referential_anchor_required(
        self,
        request_text: str,
        context: RequestNormalizationContext,
        *,
        resolved_summary: dict[str, Any] | None,
    ) -> bool:
        card = context.session_state_card
        if card is None:
            return False
        if resolved_summary is None:
            return False
        if not self._uses_referential_committed_summary_language(request_text):
            return False
        if not requires_explicit_referential_anchor(card.notes):
            return False
        return not self._has_explicit_referential_anchor(request_text, context)

    def _has_explicit_referential_anchor(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> bool:
        history = self._committed_summary_history(context)
        if self._match_explicit_commit_reference(request_text, history) is not None:
            return True
        if self._uses_second_latest_reference_language(request_text):
            return True
        explicit_node_refs = self._resolve_node_refs(self._extract_node_refs(request_text), context)
        return bool(explicit_node_refs)


    def _pending_anchor_snapshot_for_request(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> dict[str, Any]:
        card = context.session_state_card
        if card is None:
            return {}
        if not self._uses_referential_committed_summary_language(request_text):
            return {}
        snapshot = governance_pending_anchor_snapshot_from_notes(card.notes)
        if not snapshot:
            return {}
        if self._has_explicit_referential_anchor(request_text, context):
            return {}
        return snapshot

    def _latest_committed_summary(self, context: RequestNormalizationContext) -> dict[str, Any] | None:
        card = context.session_state_card
        if card is None:
            return None
        primary = card.notes.get("committed_summary_primary")
        if isinstance(primary, dict):
            return dict(primary)
        history = self._committed_summary_history(context)
        if history:
            return history[0]
        return None

    def _committed_summary_history(self, context: RequestNormalizationContext) -> list[dict[str, Any]]:
        card = context.session_state_card
        if card is None:
            return []
        history = card.notes.get("commit_summary_history")
        if not isinstance(history, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in history:
            if isinstance(item, dict):
                normalized.append(dict(item))
        return normalized

    def _uses_referential_committed_summary_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\bprevious change\b",
            r"\blast change\b",
            r"\bprevious commit\b",
            r"\blast commit\b",
            r"\bsame change\b",
            r"\bsame edit\b",
            r"\bthat change\b",
            r"\bthat edit\b",
            r"\brevert\b",
            r"\bundo\b",
            r"\brollback\b",
            r"\broll back\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)


    def _resolve_committed_summary_reference(
        self,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> tuple[dict[str, Any] | None, str | None, str | None]:
        if not self._uses_referential_committed_summary_language(request_text):
            return None, None, None
        history = self._committed_summary_history(context)
        latest_summary = self._latest_committed_summary(context)
        if latest_summary is not None and (not history or history[0].get("commit_id") != latest_summary.get("commit_id")):
            history = [latest_summary, *history]
        exact_match = self._match_explicit_commit_reference(request_text, history)
        if exact_match is not None:
            return exact_match, "exact_commit_match", None
        if self._uses_second_latest_reference_language(request_text):
            if len(history) >= 2:
                return history[1], "second_latest_auto", None
            return None, None, "insufficient_history"
        if self._uses_ambiguous_nonlatest_reference_language(request_text):
            if len(history) >= 2:
                return None, None, "clarification_required"
            if len(history) == 1:
                return None, None, "insufficient_history"
            return None, None, "missing"
        if latest_summary is not None:
            return latest_summary, "latest_auto", None
        return None, None, "missing"

    def _match_explicit_commit_reference(
        self,
        request_text: str,
        history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        text = request_text.casefold()
        commit_tokens = set(re.findall(r"\b[a-f0-9]{7,40}\b", text))
        if not commit_tokens:
            return None
        for item in history:
            commit_id = item.get("commit_id", "").casefold()
            if any(commit_id.startswith(token) for token in commit_tokens):
                return item
        return None

    def _uses_second_latest_reference_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\b(second last|second-latest|before last|prior to last|the one before that) (change|commit|edit)\b",
            r"\b(change|commit|edit) before last\b",
            r"\bcommit before last\b",
            r"\bchange before last\b",
            r"\bthe one before that\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def _uses_ambiguous_nonlatest_reference_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\bolder change\b",
            r"\bearlier change\b",
            r"\bolder commit\b",
            r"\bearlier commit\b",
            r"\bnot the last (change|commit|edit)\b",
            r"\bother (change|commit|edit)\b",
            r"\bthat older (change|commit|edit)\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)


    def _uses_previous_reference_language(self, request_text: str) -> bool:
        text = request_text.casefold()
        patterns = (
            r"\bprevious change\b",
            r"\bprevious commit\b",
            r"\bthat previous change\b",
            r"\bthat previous commit\b",
        )
        return any(re.search(pattern, text) for pattern in patterns)


    def _committed_summary_touched_node_ids(
        self,
        summary: dict[str, Any] | None,
        context: RequestNormalizationContext,
    ) -> tuple[str, ...]:
        if summary is None:
            return ()
        raw = summary.get("touched_node_ids")
        if not isinstance(raw, (list, tuple)):
            return ()
        refs = tuple(str(item) for item in raw if str(item).strip())
        return self._resolve_node_refs(refs, context)

    def _resolve_target_node_refs_from_committed_summary(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
        explicit_node_refs: tuple[str, ...],
    ) -> tuple[str, ...]:
        if category not in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"}:
            return explicit_node_refs
        summary, _, _ = self._resolve_committed_summary_reference(request_text, context)
        if summary is None:
            return explicit_node_refs
        touched_node_ids = self._committed_summary_touched_node_ids(summary, context)
        if explicit_node_refs:
            return explicit_node_refs
        if len(touched_node_ids) == 1:
            return touched_node_ids
        return explicit_node_refs

    def _first_target_ref(self, scope: TargetScope, request_text: str) -> str | None:
        if scope.node_refs:
            return scope.node_refs[0]
        return self._first_node_ref(request_text)

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
