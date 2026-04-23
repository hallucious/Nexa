from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.contracts.designer_contract import CHANGE_SCOPE_LEVELS, PATCH_MODES, PATCH_OPERATION_TYPES, TOUCH_MODES

DESTRUCTIVE_PATCH_OPERATION_TYPES = {
    "delete_node",
    "disconnect_nodes",
    "remove_output_binding",
    "delete_subgraph",
}


@dataclass(frozen=True)
class ChangeScope:
    scope_level: str
    touch_mode: str
    touched_nodes: tuple[str, ...] = ()
    touched_edges: tuple[str, ...] = ()
    touched_outputs: tuple[str, ...] = ()
    touched_metadata: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.scope_level not in CHANGE_SCOPE_LEVELS:
            raise ValueError(f"Unsupported change scope level: {self.scope_level}")
        if self.touch_mode not in TOUCH_MODES:
            raise ValueError(f"Unsupported touch_mode: {self.touch_mode}")


@dataclass(frozen=True)
class PatchOperation:
    op_id: str
    op_type: str
    target_ref: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    depends_on_ops: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.op_id.strip():
            raise ValueError("PatchOperation.op_id must be non-empty")
        if self.op_type not in PATCH_OPERATION_TYPES:
            raise ValueError(f"Unsupported patch operation type: {self.op_type}")
        if self.op_type in DESTRUCTIVE_PATCH_OPERATION_TYPES and not self.rationale.strip():
            raise ValueError("Destructive PatchOperation entries must include rationale")


@dataclass(frozen=True)
class DependencyEffectReport:
    affected_upstream_nodes: tuple[str, ...] = ()
    affected_downstream_nodes: tuple[str, ...] = ()
    broken_paths_if_unapplied: tuple[str, ...] = ()
    newly_created_paths: tuple[str, ...] = ()
    removed_paths: tuple[str, ...] = ()
    dependency_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutputEffectReport:
    previous_outputs: tuple[str, ...] = ()
    proposed_outputs: tuple[str, ...] = ()
    added_outputs: tuple[str, ...] = ()
    removed_outputs: tuple[str, ...] = ()
    modified_outputs: tuple[str, ...] = ()
    output_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class PatchRiskReport:
    risks: tuple[str, ...] = ()
    requires_confirmation: bool = False
    blocking_risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.blocking_risks and not self.requires_confirmation:
            raise ValueError("PatchRiskReport.requires_confirmation must be true when blocking_risks are present")


@dataclass(frozen=True)
class ReversibilitySpec:
    reversible: bool
    rollback_strategy: str | None = None
    rollback_requirements: tuple[str, ...] = ()
    destructive_ops_present: bool = False

    def __post_init__(self) -> None:
        if not self.reversible and not self.rollback_strategy and self.destructive_ops_present:
            raise ValueError(
                "ReversibilitySpec.rollback_strategy is required when destructive_ops_present is true and reversible is false"
            )


@dataclass(frozen=True)
class PreviewRequirements:
    required_preview_areas: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationRequirements:
    required_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class CircuitPatchPlan:
    patch_id: str
    patch_mode: str
    summary: str
    intent_ref: str
    change_scope: ChangeScope
    operations: tuple[PatchOperation, ...]
    dependency_effects: DependencyEffectReport = field(default_factory=DependencyEffectReport)
    output_effects: OutputEffectReport = field(default_factory=OutputEffectReport)
    risk_report: PatchRiskReport = field(default_factory=PatchRiskReport)
    reversibility: ReversibilitySpec = field(default_factory=lambda: ReversibilitySpec(reversible=True))
    preview_requirements: PreviewRequirements = field(default_factory=PreviewRequirements)
    validation_requirements: ValidationRequirements = field(default_factory=ValidationRequirements)
    target_savefile_ref: str | None = None
    target_circuit_ref: str | None = None
    based_on_revision: str | None = None

    def __post_init__(self) -> None:
        if not self.patch_id.strip():
            raise ValueError("CircuitPatchPlan.patch_id must be non-empty")
        if self.patch_mode not in PATCH_MODES:
            raise ValueError(f"Unsupported patch_mode: {self.patch_mode}")
        if not self.summary.strip():
            raise ValueError("CircuitPatchPlan.summary must be non-empty")
        if not self.intent_ref.strip():
            raise ValueError("CircuitPatchPlan.intent_ref must be non-empty")
        if not self.operations:
            raise ValueError("CircuitPatchPlan.operations must not be empty")
        op_ids = [op.op_id for op in self.operations]
        if len(op_ids) != len(set(op_ids)):
            raise ValueError("CircuitPatchPlan.operations must have unique op_id values")
        declared_ids = set(op_ids)
        for op in self.operations:
            unknown_dependencies = set(op.depends_on_ops) - declared_ids
            if unknown_dependencies:
                raise ValueError(
                    f"PatchOperation {op.op_id} references unknown depends_on_ops: {sorted(unknown_dependencies)}"
                )
        if self.patch_mode == "create_draft" and self.target_savefile_ref is not None:
            raise ValueError("CircuitPatchPlan.target_savefile_ref must be omitted for create_draft mode")
        if self.risk_report.blocking_risks and self.change_scope.touch_mode == "read_only":
            raise ValueError("read_only patch plans may not declare blocking risks")
