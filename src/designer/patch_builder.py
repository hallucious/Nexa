from __future__ import annotations

from src.designer.models.circuit_patch_plan import (
    ChangeScope,
    CircuitPatchPlan,
    DependencyEffectReport,
    OutputEffectReport,
    PatchOperation,
    PatchRiskReport,
    PreviewRequirements,
    ReversibilitySpec,
    ValidationRequirements,
)
from src.designer.models.designer_intent import DesignerIntent

PATCH_MODE_BY_CATEGORY = {
    "CREATE_CIRCUIT": "create_draft",
    "MODIFY_CIRCUIT": "modify_existing",
    "REPAIR_CIRCUIT": "repair_existing",
    "OPTIMIZE_CIRCUIT": "optimize_existing",
}

PATCH_OPERATION_BY_ACTION = {
    "create_node": "create_node",
    "delete_node": "delete_node",
    "update_node": "update_node_metadata",
    "connect_nodes": "connect_nodes",
    "disconnect_nodes": "disconnect_nodes",
    "insert_node_between": "insert_node_between",
    "replace_provider": "set_node_provider",
    "attach_plugin": "attach_node_plugin",
    "detach_plugin": "detach_node_plugin",
    "set_prompt": "set_node_prompt",
    "set_parameter": "set_parameter",
    "add_review_gate": "create_node",
    "remove_review_gate": "delete_node",
    "define_output": "define_output_binding",
    "rename_component": "rename_node",
}

DESTRUCTIVE_OPS = {"delete_node", "disconnect_nodes", "remove_output_binding", "delete_subgraph"}
OUTPUT_OPS = {"define_output_binding", "remove_output_binding", "move_output_binding"}


class CircuitPatchBuilder:
    def build(self, intent: DesignerIntent) -> CircuitPatchPlan:
        if intent.category not in PATCH_MODE_BY_CATEGORY:
            raise ValueError(f"Step 2 proposal flow does not support non-mutating category: {intent.category}")
        operations = tuple(self._build_operations(intent))
        if not operations and not self._allows_confirmation_only_patch(intent):
            raise ValueError("CircuitPatchBuilder requires at least one explicit operation")
        change_scope = self._build_change_scope(intent, operations)
        dependency_effects = self._build_dependency_effects(operations)
        output_effects = self._build_output_effects(operations)
        risk_report = self._build_risk_report(intent, operations)
        reversibility = self._build_reversibility(operations)
        preview_requirements = PreviewRequirements(
            required_preview_areas=(
                "summary",
                "structural_delta",
                "node_changes",
                "edge_changes",
                "output_changes",
                "risk",
                "cost",
                "assumptions",
                "confirmation",
            )
        )
        validation_requirements = ValidationRequirements(
            required_checks=(
                "structural_validity",
                "dependency_validity",
                "input_output_validity",
                "provider_resolution",
                "plugin_resolution",
                "safety_review",
                "cost_assessment",
                "ambiguity_assessment",
            )
        )
        return CircuitPatchPlan(
            patch_id=intent.intent_id.replace("intent-", "patch-"),
            patch_mode=PATCH_MODE_BY_CATEGORY[intent.category],
            target_savefile_ref=intent.target_scope.savefile_ref,
            summary=self._build_summary(intent, change_scope),
            intent_ref=intent.intent_id,
            change_scope=change_scope,
            operations=operations,
            dependency_effects=dependency_effects,
            output_effects=output_effects,
            risk_report=risk_report,
            reversibility=reversibility,
            preview_requirements=preview_requirements,
            validation_requirements=validation_requirements,
        )

    def _allows_confirmation_only_patch(self, intent: DesignerIntent) -> bool:
        return bool(intent.requires_user_confirmation and intent.ambiguity_flags)

    def _build_operations(self, intent: DesignerIntent) -> list[PatchOperation]:
        operations: list[PatchOperation] = []
        for index, action in enumerate(intent.proposed_actions, start=1):
            op_type = PATCH_OPERATION_BY_ACTION[action.action_type]
            payload = dict(action.parameters)
            if action.action_type == "add_review_gate":
                payload.setdefault("kind", "review_gate")
                payload.setdefault("requires_confirmation", True)
            if action.action_type == "define_output":
                payload.setdefault("output_ref", action.target_ref or "output.final")
            operations.append(
                PatchOperation(
                    op_id=f"op-{index}",
                    op_type=op_type,
                    target_ref=action.target_ref,
                    payload=payload,
                    rationale=action.rationale,
                    depends_on_ops=(),
                )
            )
        if not operations and self._allows_confirmation_only_patch(intent):
            operations.append(self._confirmation_only_operation(intent))
        return operations

    def _confirmation_only_operation(self, intent: DesignerIntent) -> PatchOperation:
        mixed_reason_codes = tuple(
            flag.type.upper() for flag in intent.ambiguity_flags if flag.type.startswith("mixed_referential_")
        )
        return PatchOperation(
            op_id="op-confirmation-only",
            op_type="update_node_metadata",
            target_ref=None,
            payload={
                "confirmation_only": True,
                "reason_codes": mixed_reason_codes,
            },
            rationale="Confirmation-bounded proposal placeholder; structural operations will be generated after clarification.",
            depends_on_ops=(),
        )

    def _build_change_scope(self, intent: DesignerIntent, operations: tuple[PatchOperation, ...]) -> ChangeScope:
        destructive = any(op.op_type in DESTRUCTIVE_OPS for op in operations)
        touch_mode = "destructive_edit" if destructive else "structural_edit"
        if intent.category == "CREATE_CIRCUIT":
            touch_mode = "append_only"
        touched_nodes = tuple(sorted({op.target_ref for op in operations if op.target_ref and not op.op_type.endswith("output_binding")}))
        touched_outputs = tuple(sorted({op.payload.get("output_ref") or op.target_ref for op in operations if op.op_type in OUTPUT_OPS and (op.payload.get("output_ref") or op.target_ref)}))
        return ChangeScope(
            scope_level=intent.target_scope.max_change_scope,
            touch_mode=touch_mode,
            touched_nodes=touched_nodes,
            touched_edges=(),
            touched_outputs=touched_outputs,
            touched_metadata=(),
        )

    def _build_dependency_effects(self, operations: tuple[PatchOperation, ...]) -> DependencyEffectReport:
        new_paths = tuple(op.target_ref for op in operations if op.op_type in {"connect_nodes", "insert_node_between"} and op.target_ref)
        removed_paths = tuple(op.target_ref for op in operations if op.op_type == "disconnect_nodes" and op.target_ref)
        risks = []
        if removed_paths:
            risks.append("Disconnected paths may require output rebinding.")
        if any(op.op_type == "create_node" for op in operations):
            risks.append("New nodes should be checked for provider/plugin/resource resolution.")
        return DependencyEffectReport(
            newly_created_paths=new_paths,
            removed_paths=removed_paths,
            dependency_risks=tuple(risks),
        )

    def _build_output_effects(self, operations: tuple[PatchOperation, ...]) -> OutputEffectReport:
        added = tuple(sorted({op.payload.get("output_ref") or op.target_ref for op in operations if op.op_type == "define_output_binding" and (op.payload.get("output_ref") or op.target_ref)}))
        removed = tuple(sorted({op.payload.get("output_ref") or op.target_ref for op in operations if op.op_type == "remove_output_binding" and (op.payload.get("output_ref") or op.target_ref)}))
        modified = tuple(sorted({op.payload.get("output_ref") or op.target_ref for op in operations if op.op_type == "move_output_binding" and (op.payload.get("output_ref") or op.target_ref)}))
        risks = tuple(
            [
                "Output semantics may change and should be reviewed."
                for _ in [1]
                if added or removed or modified
            ]
        )
        return OutputEffectReport(
            previous_outputs=(),
            proposed_outputs=tuple(sorted(set(added + modified))),
            added_outputs=added,
            removed_outputs=removed,
            modified_outputs=modified,
            output_risks=risks,
        )

    def _build_risk_report(self, intent: DesignerIntent, operations: tuple[PatchOperation, ...]) -> PatchRiskReport:
        risk_messages = [flag.description for flag in intent.risk_flags]
        blocking = [flag.description for flag in intent.risk_flags if flag.severity == "high"]
        if any(op.op_type in DESTRUCTIVE_OPS for op in operations):
            risk_messages.append("Destructive edit requested.")
            blocking.append("Destructive edit requested.")
        return PatchRiskReport(
            risks=tuple(risk_messages),
            requires_confirmation=bool(intent.requires_user_confirmation or blocking),
            blocking_risks=tuple(blocking),
        )

    def _build_reversibility(self, operations: tuple[PatchOperation, ...]) -> ReversibilitySpec:
        destructive = any(op.op_type in DESTRUCTIVE_OPS for op in operations)
        return ReversibilitySpec(
            reversible=not destructive,
            rollback_strategy="restore_working_save_revision" if destructive else None,
            rollback_requirements=("working_save_revision",) if destructive else (),
            destructive_ops_present=destructive,
        )

    def _build_summary(self, intent: DesignerIntent, change_scope: ChangeScope) -> str:
        if not intent.proposed_actions and intent.requires_user_confirmation:
            return f"{intent.category} proposal is confirmation-bounded and requires clarification before structural operations can be generated."
        return f"{intent.category} proposal with {change_scope.scope_level} scope and {change_scope.touch_mode} touch mode."
