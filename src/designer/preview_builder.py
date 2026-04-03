from __future__ import annotations

from src.designer.models.circuit_draft_preview import (
    AssumptionPreview,
    BehaviorChangePreview,
    CircuitDraftPreview,
    ConfirmationPreview,
    CostPreview,
    EdgeChangeCard,
    EdgeChangePreview,
    EdgeSummary,
    GraphViewModel,
    NodeChangeCard,
    NodeChangePreview,
    OutputChangeCard,
    OutputChangePreview,
    RiskPreview,
    StructuralPreview,
    SummaryCard,
)
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.validation_precheck import ValidationPrecheck


class DesignerPreviewBuilder:
    def build(self, intent: DesignerIntent, patch: CircuitPatchPlan, precheck: ValidationPrecheck) -> CircuitDraftPreview:
        preview_mode = {
            "CREATE_CIRCUIT": "draft_create",
            "MODIFY_CIRCUIT": "patch_modify",
            "REPAIR_CIRCUIT": "repair_preview",
            "OPTIMIZE_CIRCUIT": "optimize_preview",
        }[intent.category]
        structural_preview = self._structural_preview(patch)
        node_preview = self._node_change_preview(patch)
        edge_preview = self._edge_change_preview(patch)
        output_preview = self._output_change_preview(patch)
        summary = SummaryCard(
            title=self._title(intent),
            one_sentence_summary=self._one_sentence_summary(intent, patch, precheck),
            proposal_type={
                "CREATE_CIRCUIT": "create",
                "MODIFY_CIRCUIT": "modify",
                "REPAIR_CIRCUIT": "repair",
                "OPTIMIZE_CIRCUIT": "optimize",
            }[intent.category],
            change_scope=patch.change_scope.scope_level,
            touched_node_count=max(len(node_preview.cards), len(structural_preview.added_nodes) + len(structural_preview.removed_nodes) + len(structural_preview.modified_nodes)),
            touched_edge_count=max(len(edge_preview.cards), len(structural_preview.added_edges) + len(structural_preview.removed_edges)),
            touched_output_count=max(len(output_preview.cards), len(structural_preview.changed_outputs)),
            overall_status={
                "pass": "safe_to_preview",
                "pass_with_warnings": "warning_present",
                "confirmation_required": "confirmation_required",
                "blocked": "blocked",
            }[precheck.overall_status],
            user_action_hint=self._user_action_hint(precheck),
        )
        return CircuitDraftPreview(
            preview_id=patch.patch_id.replace("patch-", "preview-"),
            intent_ref=intent.intent_id,
            patch_ref=patch.patch_id,
            precheck_ref=precheck.precheck_id,
            preview_mode=preview_mode,
            summary_card=summary,
            structural_preview=structural_preview,
            node_change_preview=node_preview,
            edge_change_preview=edge_preview,
            output_change_preview=output_preview,
            behavior_change_preview=BehaviorChangePreview(
                summary=self._behavior_summary(intent, patch),
                expected_effects=self._expected_effects(intent, patch),
                possible_regressions=tuple(f.message for f in precheck.warning_findings),
            ),
            risk_preview=RiskPreview(
                summary=self._risk_summary(precheck),
                risks=tuple(f.message for f in (*precheck.warning_findings, *precheck.confirmation_findings, *precheck.blocking_findings)),
                requires_confirmation=precheck.overall_status == "confirmation_required",
            ),
            cost_preview=CostPreview(
                cost_summary=precheck.cost_assessment.summary or "Cost impact not estimated.",
                estimated_cost_change=precheck.cost_assessment.estimated_cost_impact,
                complexity_change="higher" if patch.change_scope.scope_level == "broad" else "bounded",
            ),
            assumption_preview=AssumptionPreview(
                assumptions=tuple(assumption.text for assumption in intent.assumptions),
                default_choices=self._default_choices(intent),
            ),
            confirmation_preview=ConfirmationPreview(
                required_confirmations=tuple(f.message for f in precheck.confirmation_findings),
                auto_commit_allowed=False,
            ),
            graph_view_model=GraphViewModel(
                node_count=max(structural_preview.before_node_count, structural_preview.after_node_count),
                edge_count=max(structural_preview.before_edge_count, structural_preview.after_edge_count),
                annotations={"preview_mode": preview_mode},
            ),
            explanation=precheck.explanation,
        )

    def _title(self, intent: DesignerIntent) -> str:
        return {
            "CREATE_CIRCUIT": "Create new circuit proposal",
            "MODIFY_CIRCUIT": "Modify existing circuit proposal",
            "REPAIR_CIRCUIT": "Repair circuit proposal",
            "OPTIMIZE_CIRCUIT": "Optimize circuit proposal",
        }[intent.category]

    def _one_sentence_summary(self, intent: DesignerIntent, patch: CircuitPatchPlan, precheck: ValidationPrecheck) -> str:
        return f"{patch.summary} Current precheck status: {precheck.overall_status}."

    def _structural_preview(self, patch: CircuitPatchPlan) -> StructuralPreview:
        added_nodes = tuple(sorted({op.target_ref for op in patch.operations if op.op_type == "create_node" and op.target_ref}))
        removed_nodes = tuple(sorted({op.target_ref for op in patch.operations if op.op_type == "delete_node" and op.target_ref}))
        modified_nodes = tuple(sorted({op.target_ref for op in patch.operations if op.op_type not in {"create_node", "delete_node"} and op.target_ref and not op.op_type.endswith("output_binding")}))
        added_edges = tuple(
            EdgeSummary(from_node=op.payload.get("from_node", "unknown"), to_node=op.payload.get("to_node", op.target_ref or "unknown"))
            for op in patch.operations
            if op.op_type in {"connect_nodes", "insert_node_between"}
        )
        removed_edges = tuple(
            EdgeSummary(from_node=op.payload.get("from_node", "unknown"), to_node=op.payload.get("to_node", op.target_ref or "unknown"))
            for op in patch.operations
            if op.op_type == "disconnect_nodes"
        )
        changed_outputs = tuple(sorted(set(patch.output_effects.added_outputs + patch.output_effects.modified_outputs + patch.output_effects.removed_outputs)))
        before_nodes = len(removed_nodes) + len(modified_nodes)
        after_nodes = before_nodes + len(added_nodes)
        before_edges = len(removed_edges)
        after_edges = len(added_edges) + before_edges
        return StructuralPreview(
            before_exists=patch.patch_mode != "create_draft",
            before_node_count=before_nodes,
            after_node_count=after_nodes,
            before_edge_count=before_edges,
            after_edge_count=after_edges,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            changed_outputs=changed_outputs,
            structural_delta_summary=self._structural_summary(added_nodes, removed_nodes, modified_nodes, changed_outputs),
        )

    def _node_change_preview(self, patch: CircuitPatchPlan) -> NodeChangePreview:
        cards: list[NodeChangeCard] = []
        for op in patch.operations:
            mapping = {
                "create_node": "created",
                "delete_node": "deleted",
                "set_node_provider": "provider_changed",
                "set_node_prompt": "prompt_changed",
                "attach_node_plugin": "plugin_changed",
                "detach_node_plugin": "plugin_changed",
                "set_parameter": "parameter_changed",
                "update_node_metadata": "role_changed",
                "rename_node": "role_changed",
                "insert_node_between": "created",
            }
            if op.op_type not in mapping or not op.target_ref:
                continue
            cards.append(
                NodeChangeCard(
                    node_ref=op.target_ref,
                    change_type=mapping[op.op_type],
                    before_summary=None if mapping[op.op_type] == "created" else f"Previous state for {op.target_ref}",
                    after_summary=None if mapping[op.op_type] == "deleted" else f"Proposed state for {op.target_ref}",
                    why_it_changed=op.rationale,
                    expected_effect=self._expected_effect_for_op(op.op_type),
                    criticality="high" if op.op_type == "delete_node" else ("medium" if op.op_type in {"set_node_provider", "attach_node_plugin", "insert_node_between"} else "low"),
                )
            )
        return NodeChangePreview(cards=tuple(cards))

    def _edge_change_preview(self, patch: CircuitPatchPlan) -> EdgeChangePreview:
        cards = []
        for op in patch.operations:
            if op.op_type == "connect_nodes":
                cards.append(EdgeChangeCard(from_node=op.payload.get("from_node", "unknown"), to_node=op.payload.get("to_node", op.target_ref or "unknown"), change_type="created", description=op.rationale))
            elif op.op_type == "disconnect_nodes":
                cards.append(EdgeChangeCard(from_node=op.payload.get("from_node", "unknown"), to_node=op.payload.get("to_node", op.target_ref or "unknown"), change_type="deleted", description=op.rationale))
            elif op.op_type == "insert_node_between":
                cards.append(EdgeChangeCard(from_node=op.payload.get("from_node", "upstream"), to_node=op.target_ref or "inserted", change_type="created", description=op.rationale))
        return EdgeChangePreview(cards=tuple(cards))

    def _output_change_preview(self, patch: CircuitPatchPlan) -> OutputChangePreview:
        cards = []
        for name in patch.output_effects.added_outputs:
            cards.append(OutputChangeCard(output_ref=name, change_type="created", after_summary=f"New output '{name}'."))
        for name in patch.output_effects.removed_outputs:
            cards.append(OutputChangeCard(output_ref=name, change_type="deleted", before_summary=f"Existing output '{name}'."))
        for name in patch.output_effects.modified_outputs:
            cards.append(OutputChangeCard(output_ref=name, change_type="modified", before_summary=f"Existing binding for '{name}'.", after_summary=f"Updated binding for '{name}'."))
        return OutputChangePreview(cards=tuple(cards))

    def _user_action_hint(self, precheck: ValidationPrecheck) -> str:
        if precheck.overall_status == "blocked":
            return "Revise the proposal before attempting approval."
        if precheck.overall_status == "confirmation_required":
            return "Review the confirmation items before approving the proposal."
        if precheck.overall_status == "pass_with_warnings":
            return "Review the warnings, then approve if acceptable."
        return "Review the preview and continue when ready."

    def _behavior_summary(self, intent: DesignerIntent, patch: CircuitPatchPlan) -> str:
        return f"This proposal changes circuit behavior through {len(patch.operations)} explicit patch operation(s)."

    def _expected_effects(self, intent: DesignerIntent, patch: CircuitPatchPlan) -> tuple[str, ...]:
        effects = [self._expected_effect_for_op(op.op_type) for op in patch.operations]
        deduped: list[str] = []
        for effect in effects:
            if effect not in deduped:
                deduped.append(effect)
        return tuple(deduped)

    def _expected_effect_for_op(self, op_type: str) -> str:
        return {
            "create_node": "Introduces new circuit capability.",
            "delete_node": "Removes an existing structural behavior.",
            "set_node_provider": "Changes provider-backed behavior and cost.",
            "set_node_prompt": "Changes instruction behavior.",
            "attach_node_plugin": "Adds tool-mediated behavior.",
            "detach_node_plugin": "Removes tool-mediated behavior.",
            "set_parameter": "Tunes bounded behavior without replacing structure.",
            "update_node_metadata": "Adjusts node semantics/metadata.",
            "rename_node": "Clarifies node identity without changing runtime semantics.",
            "insert_node_between": "Adds an intermediate review or transformation step.",
            "connect_nodes": "Creates a new dependency path.",
            "disconnect_nodes": "Removes a dependency path.",
            "define_output_binding": "Adds a new exposed output.",
        }.get(op_type, "Adjusts the proposed circuit behavior.")

    def _risk_summary(self, precheck: ValidationPrecheck) -> str:
        if precheck.overall_status == "blocked":
            return "Blocking issues must be resolved before approval."
        if precheck.overall_status == "confirmation_required":
            return "The proposal is previewable, but explicit confirmation is required."
        if precheck.overall_status == "pass_with_warnings":
            return "The proposal is previewable with warnings."
        return "No blocking issues were found for preview."

    def _default_choices(self, intent: DesignerIntent) -> tuple[str, ...]:
        defaults: list[str] = []
        if intent.constraints.provider_preferences:
            defaults.append(f"Preferred provider: {intent.constraints.provider_preferences[0]}")
        if intent.constraints.human_review_required:
            defaults.append("Manual review remains enabled.")
        return tuple(defaults)

    def _structural_summary(
        self,
        added_nodes: tuple[str, ...],
        removed_nodes: tuple[str, ...],
        modified_nodes: tuple[str, ...],
        changed_outputs: tuple[str, ...],
    ) -> str:
        parts = []
        if added_nodes:
            parts.append(f"adds {len(added_nodes)} node(s)")
        if removed_nodes:
            parts.append(f"removes {len(removed_nodes)} node(s)")
        if modified_nodes:
            parts.append(f"modifies {len(modified_nodes)} node(s)")
        if changed_outputs:
            parts.append(f"changes {len(changed_outputs)} output binding(s)")
        return ", ".join(parts) if parts else "No structural delta detected."
