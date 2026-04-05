from __future__ import annotations

from src.designer.control_governance import governance_decision_for_request
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_intent import DesignerIntent
from src.designer.reason_codes import (
    confirmation_message_for_reason_code,
    is_mixed_referential_flag_type,
    reason_code_for_flag_type,
)
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    PrecheckFinding,
    PreviewRequirements,
    ResolutionReport,
    ValidationPrecheck,
    ValidityReport,
)


class DesignerPrecheckBuilder:
    def build(self, intent: DesignerIntent, patch: CircuitPatchPlan, *, session_state_card=None) -> ValidationPrecheck:
        governance_decision = self._governance_decision(intent, session_state_card=session_state_card)
        blocking_findings = list(self._blocking_findings(intent, patch))
        warning_findings = list(self._warning_findings(intent, patch, session_state_card=session_state_card, governance_decision=governance_decision))
        confirmation_findings = list(self._confirmation_findings(intent, patch, blocking_findings, session_state_card=session_state_card, governance_decision=governance_decision))
        overall_status = self._overall_status(blocking_findings, confirmation_findings, warning_findings)
        evaluated_scope = EvaluatedScope(
            mode=self._evaluated_scope_mode(intent),
            savefile_ref=intent.target_scope.savefile_ref,
            touched_nodes=patch.change_scope.touched_nodes,
            touched_edges=patch.change_scope.touched_edges,
            touched_outputs=patch.change_scope.touched_outputs,
            touch_summary=f"{patch.change_scope.scope_level} scope touching {len(patch.change_scope.touched_nodes)} node(s).",
        )
        structural_status = "blocked" if blocking_findings else ("warning" if warning_findings else "valid")
        ambiguity_status = "confirmation_required" if confirmation_findings else ("warning" if intent.ambiguity_flags else "clear")
        return ValidationPrecheck(
            precheck_id=patch.patch_id.replace("patch-", "precheck-"),
            patch_ref=patch.patch_id,
            intent_ref=intent.intent_id,
            evaluated_scope=evaluated_scope,
            overall_status=overall_status,
            structural_validity=ValidityReport(status=structural_status, summary="Structural proposal checks completed.", findings=tuple(blocking_findings + warning_findings)),
            dependency_validity=ValidityReport(status="warning" if patch.dependency_effects.dependency_risks else "valid", summary="Dependency effects evaluated."),
            input_output_validity=ValidityReport(status="warning" if patch.output_effects.output_risks else "valid", summary="Output impact evaluated."),
            provider_resolution=ResolutionReport(status="warning" if self._provider_warnings(patch) else "resolved", summary="Provider references normalized."),
            plugin_resolution=ResolutionReport(status="warning" if self._plugin_warnings(patch) else "resolved", summary="Plugin references normalized."),
            safety_review=ValidityReport(status="warning" if confirmation_findings else "valid", summary="Safety review requires explicit approval when confirmation is present."),
            cost_assessment=CostAssessmentReport(status="warning" if self._cost_warning(intent, patch) else "acceptable", summary="Cost impact estimated.", estimated_cost_impact=self._estimated_cost_impact(intent, patch)),
            ambiguity_assessment=AmbiguityAssessmentReport(status=ambiguity_status, summary="Ambiguity was evaluated for preview/approval readiness.", findings=tuple(confirmation_findings)),
            preview_requirements=PreviewRequirements(required_sections=("summary", "structural", "risk", "confirmation", "cost", "assumptions")),
            blocking_findings=tuple(blocking_findings),
            warning_findings=tuple(warning_findings),
            confirmation_findings=tuple(confirmation_findings),
            recommended_next_actions=self._recommended_next_actions(overall_status, governance_decision=governance_decision),
            explanation=self._build_explanation(overall_status, governance_decision=governance_decision),
        )

    def _evaluated_scope_mode(self, intent: DesignerIntent) -> str:
        return {
            "new_circuit": "new_circuit",
            "existing_circuit": "existing_circuit_patch",
            "subgraph_only": "subgraph_patch",
            "node_only": "node_patch",
            "read_only": "node_patch",
        }[intent.target_scope.mode]

    def _blocking_findings(self, intent: DesignerIntent, patch: CircuitPatchPlan) -> tuple[PrecheckFinding, ...]:
        findings: list[PrecheckFinding] = []
        if not patch.operations and not self._allows_confirmation_only_preview(intent):
            findings.append(PrecheckFinding(issue_code="PATCH_EMPTY", message="No patch operations were generated.", severity="high"))
        if patch.change_scope.touch_mode == "read_only":
            findings.append(
                PrecheckFinding(
                    issue_code="READ_ONLY_PATCH",
                    message="Read-only proposals cannot cross the commit boundary.",
                    severity="high",
                )
            )
        return tuple(findings)

    def _governance_decision(self, intent: DesignerIntent, *, session_state_card=None):
        if session_state_card is None:
            return None
        return governance_decision_for_request(
            ambiguity_flags=intent.ambiguity_flags,
            proposed_actions=intent.proposed_actions,
            notes=session_state_card.notes,
        )

    def _warning_findings(self, intent: DesignerIntent, patch: CircuitPatchPlan, *, session_state_card=None, governance_decision=None) -> tuple[PrecheckFinding, ...]:
        findings: list[PrecheckFinding] = []
        if patch.dependency_effects.dependency_risks:
            findings.append(
                PrecheckFinding(
                    issue_code="DEPENDENCY_REVIEW",
                    message="Dependency changes should be reviewed before approval.",
                    severity="medium",
                )
            )
        if self._cost_warning(intent, patch):
            findings.append(
                PrecheckFinding(
                    issue_code="COST_WARNING",
                    message="The proposal may increase latency or cost.",
                    severity="low",
                )
            )
        governance_warning = self._governance_anchor_warning_finding(intent, governance_decision=governance_decision)
        if governance_warning is not None:
            findings.append(governance_warning)
        return tuple(findings)

    def _confirmation_findings(
        self,
        intent: DesignerIntent,
        patch: CircuitPatchPlan,
        blocking_findings: list[PrecheckFinding],
        *,
        session_state_card=None,
        governance_decision=None,
    ) -> tuple[PrecheckFinding, ...]:
        if blocking_findings:
            return ()
        findings: list[PrecheckFinding] = []
        mixed_reason_findings = self._mixed_referential_confirmation_findings(intent)
        if intent.ambiguity_flags and not mixed_reason_findings:
            findings.append(
                PrecheckFinding(
                    issue_code="AMBIGUOUS_TARGET",
                    message="The mutation target or scope should be confirmed before commit.",
                    severity="medium",
                )
            )
        findings.extend(mixed_reason_findings)
        governance_finding = self._governance_anchor_confirmation_finding(intent, governance_decision=governance_decision)
        if governance_finding is not None:
            findings.append(governance_finding)
        if patch.change_scope.touch_mode == "destructive_edit":
            findings.append(
                PrecheckFinding(
                    issue_code="DESTRUCTIVE_EDIT",
                    message="The proposal contains destructive structural edits.",
                    severity="high",
                )
            )
        if patch.change_scope.scope_level == "broad":
            findings.append(
                PrecheckFinding(
                    issue_code="BROAD_SCOPE_CONFIRMATION",
                    message="Broad-scope changes require explicit confirmation.",
                    severity="medium",
                )
            )
        if any(action.action_type == "add_review_gate" for action in intent.proposed_actions):
            findings.append(
                PrecheckFinding(
                    issue_code="REVIEW_GATE_CONFIRMATION",
                    message="The proposal introduces a manual review boundary that should be confirmed.",
                    severity="medium",
                )
            )
        return tuple(findings)


    def _mixed_referential_confirmation_findings(self, intent: DesignerIntent) -> tuple[PrecheckFinding, ...]:
        findings: list[PrecheckFinding] = []
        for flag in intent.ambiguity_flags:
            if not is_mixed_referential_flag_type(flag.type):
                continue
            reason_code = reason_code_for_flag_type(flag.type)
            findings.append(
                PrecheckFinding(
                    issue_code=reason_code,
                    message=self._mixed_referential_confirmation_message(reason_code),
                    severity="medium",
                    fix_hint=(
                        "Confirm the exact intended action or split the request into separate steps before approval."
                    ),
                )
            )
        return tuple(findings)

    def _mixed_referential_confirmation_message(self, reason_code: str) -> str:
        return confirmation_message_for_reason_code(reason_code)

    def _governance_anchor_confirmation_finding(self, intent: DesignerIntent, *, governance_decision=None) -> PrecheckFinding | None:
        if governance_decision is None or governance_decision.surface_mode != "confirmation_required":
            return None
        severity = "high" if governance_decision.policy.tier == "strict" else "medium"
        return PrecheckFinding(
            issue_code=f"REFERENTIAL_GOVERNANCE_{governance_decision.policy.tier.upper()}",
            message=governance_decision.explanation or "Referential governance now requires a stronger anchor before automatic rollback interpretation may continue.",
            severity=severity,
            fix_hint=governance_decision.policy.preview_hint or governance_decision.policy.reason,
        )

    def _governance_anchor_warning_finding(self, intent: DesignerIntent, *, governance_decision=None) -> PrecheckFinding | None:
        if governance_decision is None or governance_decision.surface_mode != "warning":
            return None
        return PrecheckFinding(
            issue_code=f"REFERENTIAL_GOVERNANCE_{governance_decision.policy.tier.upper()}_ANCHORED",
            message=governance_decision.explanation,
            severity="low",
            fix_hint="The current request is anchored strongly enough to continue, but future referential edits should remain explicit while governance is elevated.",
        )

    def _overall_status(
        self,
        blocking_findings: list[PrecheckFinding],
        confirmation_findings: list[PrecheckFinding],
        warning_findings: list[PrecheckFinding],
    ) -> str:
        if blocking_findings:
            return "blocked"
        if confirmation_findings:
            return "confirmation_required"
        if warning_findings:
            return "pass_with_warnings"
        return "pass"

    def _recommended_next_actions(self, status: str, *, governance_decision=None) -> tuple[str, ...]:
        base: tuple[str, ...]
        if status == "blocked":
            base = ("revise_patch", "re-run_precheck")
        elif status == "confirmation_required":
            base = ("show_preview", "ask_for_confirmation")
        elif status == "pass_with_warnings":
            base = ("show_preview", "display_warnings")
        else:
            base = ("show_preview",)
        if governance_decision is None or not governance_decision.recommended_next_actions:
            return base
        ordered = list(base)
        for item in governance_decision.recommended_next_actions:
            if item not in ordered:
                ordered.append(item)
        return tuple(ordered)

    def _build_explanation(self, status: str, *, governance_decision=None) -> str:
        if status == "blocked":
            explanation = "The proposal cannot proceed until blocking issues are resolved."
        elif status == "confirmation_required":
            explanation = "The proposal may proceed to preview, but explicit approval or clarification is required before commit."
        elif status == "pass_with_warnings":
            explanation = "The proposal can be previewed and reviewed with warnings."
        else:
            explanation = "The proposal is ready for preview."
        if governance_decision is None or governance_decision.surface_mode == "hidden" or not governance_decision.explanation:
            return explanation
        return f"{explanation} {governance_decision.explanation}"

    def _cost_warning(self, intent: DesignerIntent, patch: CircuitPatchPlan) -> bool:
        return any(action.action_type in {"replace_provider", "attach_plugin", "add_review_gate"} for action in intent.proposed_actions)

    def _estimated_cost_impact(self, intent: DesignerIntent, patch: CircuitPatchPlan) -> str:
        return "low increase" if self._cost_warning(intent, patch) else "stable"

    def _provider_warnings(self, patch: CircuitPatchPlan) -> bool:
        return any(op.op_type == "set_node_provider" and not op.payload.get("provider_id") for op in patch.operations)

    def _plugin_warnings(self, patch: CircuitPatchPlan) -> bool:
        return any(op.op_type == "attach_node_plugin" and not op.payload.get("plugin_id") for op in patch.operations)
