from __future__ import annotations

import re
from typing import Any

from src.designer.models.designer_intent import (
    ActionSpec,
    AmbiguityFlag,
    AssumptionSpec,
    ConstraintSet,
    ObjectiveSpec,
    RiskFlag,
    TargetScope,
)
from src.designer.normalization_context import RequestNormalizationContext
from src.designer.reason_codes import (
    flag_type_for_reason_code,
    reason_code_for_mixed_referential_request,
)
from src.designer.legacy_mutation_heuristics import DesignerLegacyMutationHeuristics
from src.designer.referential_resolution_support import DesignerReferentialResolutionSupport


class DesignerIntentAssemblySupport:
    """Support subsystem for assembling normalized DesignerIntent fields.

    This keeps scope/action/assumption/ambiguity/risk construction out of
    the compatibility facade so request_normalizer.py can remain orchestration-
    oriented rather than owning a large policy/heuristic bundle inline.
    """

    def __init__(
        self,
        legacy_heuristics: DesignerLegacyMutationHeuristics,
        referential_support: DesignerReferentialResolutionSupport,
    ) -> None:
        self._legacy_heuristics = legacy_heuristics
        self._referential_support = referential_support


    def build_scope(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
    ) -> TargetScope:
        text = request_text.casefold()
        broad = any(term in text for term in ("all ", "entire", "whole", "across the circuit", "every"))
        explicit_node_refs = self._legacy_heuristics.explicit_node_refs(request_text, context)
        if not explicit_node_refs and not broad:
            selected_node_refs = self._legacy_heuristics.selected_node_refs(context)
            if len(selected_node_refs) == 1 and category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"}:
                explicit_node_refs = selected_node_refs
        node_refs = self._referential_support.resolve_target_node_refs_from_committed_summary(
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

    def build_constraints(self, request_text: str, context: RequestNormalizationContext) -> ConstraintSet:
        text = request_text.casefold()
        base = ConstraintSet(
            cost_limit="low" if "low cost" in text or "reduce cost" in text else None,
            speed_priority="high" if "faster" in text or "latency" in text else None,
            quality_priority="high" if "quality" in text or "reliable" in text else None,
            determinism_preference="high" if "determin" in text else None,
            human_review_required=self._legacy_heuristics.requests_review_gate(text) or bool(re.search(r"\bapprove\b", text, flags=re.IGNORECASE)),
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

    def build_objective(self, request_text: str, context: RequestNormalizationContext) -> ObjectiveSpec:
        card = context.session_state_card
        if card is None:
            return ObjectiveSpec(primary_goal=request_text.strip())
        return ObjectiveSpec(
            primary_goal=request_text.strip(),
            secondary_goals=card.objective.secondary_goals,
            success_criteria=card.objective.success_criteria,
            preferred_behavior=card.objective.preferred_behavior,
        )

    def build_actions(
        self,
        category: str,
        request_text: str,
        scope: TargetScope,
        context: RequestNormalizationContext,
        *,
        grounded_intent=None,
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
        if grounded_intent is not None and grounded_intent.semantic_intent.action_candidates:
            return [
                ActionSpec(
                    action_type=candidate.action_type,
                    target_ref=candidate.target_ref,
                    parameters=dict(candidate.parameters),
                    rationale=candidate.rationale or "Grounded from semantic action candidate.",
                )
                for candidate in grounded_intent.grounded_action_candidates
            ]
        actions: list[ActionSpec] = []
        if self._is_confirmation_bounded_mixed_referential_request(request_text):
            return actions
        referential_action = self._resolve_referential_action_resolution(request_text, scope, context)
        if referential_action is not None:
            actions.append(referential_action)
        if self._legacy_heuristics.requests_review_gate(text):
            actions.append(
                ActionSpec(
                    action_type="add_review_gate",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"review_type": "manual"},
                    rationale="The request explicitly asks for a review/approval step.",
                )
            )
        if self._legacy_heuristics.requests_provider_change(text, context):
            provider_id = grounded_intent.matched_provider_id if grounded_intent is not None else self._legacy_heuristics.infer_provider_id(text, context)
            actions.append(
                ActionSpec(
                    action_type="replace_provider",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"provider_id": provider_id},
                    rationale="The request explicitly changes the node provider.",
                )
            )
        if self._legacy_heuristics.requests_plugin_attach(text, context):
            actions.append(
                ActionSpec(
                    action_type="attach_plugin",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"plugin_id": grounded_intent.matched_plugin_id if grounded_intent is not None else self._legacy_heuristics.infer_plugin_id(text, context)},
                    rationale="The request explicitly introduces a plugin-backed tool step.",
                )
            )
        if self._legacy_heuristics.requests_prompt_change(text, context):
            actions.append(
                ActionSpec(
                    action_type="set_prompt",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"prompt_id": grounded_intent.matched_prompt_id if grounded_intent is not None else self._legacy_heuristics.infer_prompt_id(text, context)},
                    rationale="The request explicitly changes the prompt/instruction assignment.",
                )
            )
        if any(term in text for term in ("rename",)):
            actions.append(
                ActionSpec(
                    action_type="rename_component",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"new_name": "renamed_component"},
                    rationale="The request explicitly asks for a rename operation.",
                )
            )
        if any(term in text for term in ("remove", "delete")):
            actions.append(
                ActionSpec(
                    action_type="delete_node",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={},
                    rationale="The request explicitly removes an existing structural element.",
                )
            )
        if self._legacy_heuristics.requests_insert_between(text):
            actions.append(
                ActionSpec(
                    action_type="insert_node_between",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters=grounded_intent.insert_between_parameters if grounded_intent is not None else self._legacy_heuristics.infer_insert_between_parameters(request_text, scope, context),
                    rationale="The request explicitly inserts a node into an existing path.",
                )
            )
        if any(term in text for term in ("change", "update", "modify")) and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"mode": "bounded_update"},
                    rationale="The request asks for a bounded change to existing structure.",
                )
            )
        if category == "REPAIR_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="update_node",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
                    parameters={"repair_mode": "minimal_fix"},
                    rationale="Repair requests need a minimal corrective patch proposal.",
                )
            )
        if category == "OPTIMIZE_CIRCUIT" and not actions:
            actions.append(
                ActionSpec(
                    action_type="set_parameter",
                    target_ref=self._legacy_heuristics.first_target_ref(scope, request_text),
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
        summary, _, unresolved_reason = self._referential_support.resolve_committed_summary_reference(request_text, context)
        if summary is None or unresolved_reason is not None:
            return None
        if self._referential_support.repeated_cycle_referential_anchor_required(request_text, context, resolved_summary=summary):
            return None
        target_ref = scope.node_refs[0] if len(scope.node_refs) == 1 else None
        touched_node_ids = self._referential_support.committed_summary_touched_node_ids(summary, context)
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
            self._referential_support.uses_referential_committed_summary_language(request_text)
            and self._uses_safe_revert_action_language(request_text)
            and self._uses_conflicting_nonrevert_action_language(request_text)
        )

    def _mixed_referential_action_reason_code(self, request_text: str) -> str:
        return reason_code_for_mixed_referential_request(request_text)

    def build_assumptions(
        self,
        category: str,
        request_text: str,
        context: RequestNormalizationContext,
        *,
        raw_request_text: str | None = None,
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
        resolved_summary, resolution_mode, unresolved_reason = self._referential_support.resolve_committed_summary_reference(
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
            touched_node_ids = self._referential_support.committed_summary_touched_node_ids(resolved_summary, context)
            explicit_node_refs = self._legacy_heuristics.explicit_node_refs(request_text, context)
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
        if self._referential_support.repeated_cycle_referential_anchor_required(request_text, context, resolved_summary=resolved_summary):
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "Repeated confirmation cycles are active for referential interpretation, so auto-resolution is paused until the request includes an explicit commit anchor, explicit node target, or explicit non-latest selector."
                    ),
                    severity="medium",
                    user_visible=True,
                )
            )
            pending_anchor = self._referential_support.pending_anchor_snapshot_for_request(request_text, context)
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
        recent_resolution = self._referential_support.recent_resolution_snapshot_for_request(request_text, context)
        if recent_resolution:
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "A previous governance anchor requirement was already satisfied by an anchored retry, so the current referential cycle should not inherit unresolved pending-anchor pressure unless new ambiguity appears. "
                        f"{str(recent_resolution.get('summary', '')).strip()}".strip()
                    ),
                    severity="low",
                    user_visible=True,
                )
            )
        recent_revision_history = self._referential_support.recent_revision_history_snapshot_for_request(raw_request_text or request_text, category, context)
        if recent_revision_history:
            reopened_from_redirect_archive = bool(
                recent_revision_history.get("reopened_from_redirect_archive")
            ) or bool(
                context.session_state_card is not None
                and str(context.session_state_card.notes.get("approval_revision_recent_history_reopened_status", "")).strip()
                == "restored_from_redirect_archive"
            )
            assumption_prefix = (
                f"This request explicitly reopens a previously redirected multi-step revision thread ({recent_revision_history.get('count', 0)} step(s)); restore the latest clarified interpretation and accumulated user corrections for that older scope. "
                if reopened_from_redirect_archive
                else f"This request continues a recent multi-step revision thread ({recent_revision_history.get('count', 0)} step(s)); preserve the latest clarified interpretation and accumulated user corrections unless you intend to redirect scope. "
            )
            assumptions.append(
                AssumptionSpec(
                    text=(
                        f"{assumption_prefix}{str(recent_revision_history.get('summary', '')).strip()}".strip()
                    ),
                    severity="low",
                    user_visible=True,
                )
            )
        recent_redirect_archive = self._referential_support.recent_revision_redirect_archive_snapshot_for_request(raw_request_text or request_text, category, context)
        if recent_redirect_archive:
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "A previous revision thread was explicitly redirected away from its older scope and now remains only as background history; do not revive that older correction path unless the user explicitly reopens it. "
                        f"{str(recent_redirect_archive.get('summary', '')).strip()}".strip()
                    ),
                    severity="low",
                    user_visible=True,
                )
            )
        recent_revision_replacement = self._referential_support.recent_revision_replacement_snapshot_for_request(raw_request_text or request_text, category, context)
        if recent_revision_replacement:
            assumptions.append(
                AssumptionSpec(
                    text=(
                        "A previously reopened older revision thread has already been replaced by a newer active revision thread; preserve the newer clarified direction rather than reviving the old reopened scope. "
                        f"{str(recent_revision_replacement.get('summary', '')).strip()}".strip()
                    ),
                    severity="low",
                    user_visible=True,
                )
            )
        return assumptions

    def build_ambiguity_flags(
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
        _, resolution_mode, unresolved_reason = self._referential_support.resolve_committed_summary_reference(
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
        elif resolution_mode == "latest_auto" and self._referential_support.uses_referential_committed_summary_language(request_text):
            history = self._referential_support.committed_summary_history(context)
            if len(history) > 1 and (
                self._referential_support.uses_ambiguous_nonlatest_reference_language(request_text)
                or self._referential_support.uses_previous_reference_language(request_text)
            ):
                flags.append(
                    AmbiguityFlag(
                        type="committed_summary_reference_history",
                        description="Recent committed history exists, but the request leaves open whether a non-latest summary was intended.",
                    )
                )
        resolved_summary, _, _ = self._referential_support.resolve_committed_summary_reference(request_text, context)
        if self._referential_support.repeated_cycle_referential_anchor_required(request_text, context, resolved_summary=resolved_summary):
            pending_anchor = self._referential_support.pending_anchor_snapshot_for_request(request_text, context)
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
            touched_node_ids = self._referential_support.committed_summary_touched_node_ids(resolved_summary, context)
            explicit_node_refs = self._legacy_heuristics.explicit_node_refs(request_text, context)
            if explicit_node_refs:
                conflicting = [ref for ref in explicit_node_refs if ref not in touched_node_ids]
                if touched_node_ids and conflicting:
                    flags.append(
                        AmbiguityFlag(
                            type="committed_summary_target_conflict",
                            description="The explicit node target conflicts with the node(s) touched by the referenced committed summary.",
                        )
                    )
            elif self._referential_support.uses_referential_committed_summary_language(request_text):
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

    def build_risk_flags(self, request_text: str, context: RequestNormalizationContext) -> list[RiskFlag]:
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
        pending_anchor = self._referential_support.pending_anchor_snapshot_for_request(request_text, context)
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

