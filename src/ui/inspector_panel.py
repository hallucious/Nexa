from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel, NodeResultCard
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay


@dataclass(frozen=True)
class ObjectStatusSummary:
    overall_status: str = "unknown"
    validation_state: str | None = None
    execution_state: str | None = None
    preview_state: str | None = None
    editability: str = "unknown"
    short_label: str | None = None


@dataclass(frozen=True)
class EditableFieldView:
    field_key: str
    label: str
    value: Any
    display_value: str | None = None
    editor_type: str = "text"
    required: bool = False
    mutable: bool = True
    nullable: bool = True
    placeholder: str | None = None
    help_text: str | None = None
    validation_hint: str | None = None
    allowed_values: list[str] | None = None
    current_source: str | None = None
    change_scope: str | None = None
    dangerous: bool = False


@dataclass(frozen=True)
class ReadonlyFieldView:
    field_key: str
    label: str
    value: Any
    display_value: str | None = None
    reason_readonly: str | None = None
    help_text: str | None = None


@dataclass(frozen=True)
class InlineWarningView:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class ConstraintView:
    label: str
    message: str


@dataclass(frozen=True)
class FindingRefView:
    finding_type: str
    location_ref: str | None = None
    message: str = ""


@dataclass(frozen=True)
class PreviewChangeRefView:
    change_type: str
    target_ref: str
    message: str = ""


@dataclass(frozen=True)
class InspectorActionHint:
    action_type: str
    label: str
    enabled: bool
    reason_disabled: str | None = None


@dataclass(frozen=True)
class SelectedObjectViewModel:
    object_type: str
    object_id: str | None
    storage_role: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    status_summary: ObjectStatusSummary = field(default_factory=ObjectStatusSummary)
    editable_fields: list[EditableFieldView] = field(default_factory=list)
    readonly_fields: list[ReadonlyFieldView] = field(default_factory=list)
    warnings: list[InlineWarningView] = field(default_factory=list)
    constraints: list[ConstraintView] = field(default_factory=list)
    related_validation_findings: list[FindingRefView] = field(default_factory=list)
    related_execution_findings: list[FindingRefView] = field(default_factory=list)
    related_preview_changes: list[PreviewChangeRefView] = field(default_factory=list)
    related_actions: list[InspectorActionHint] = field(default_factory=list)
    section_order: list[str] = field(default_factory=lambda: [
        "summary",
        "editable_fields",
        "readonly_fields",
        "warnings",
        "constraints",
        "related_validation_findings",
        "related_execution_findings",
        "related_preview_changes",
        "related_actions",
    ])
    empty_state_message: str | None = None
    explanation: str | None = None


def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source) -> str:
    if source is None:
        return "none"
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _circuit_from_source(source):
    if isinstance(source, (WorkingSaveModel, CommitSnapshotModel)):
        return source.circuit
    return None


def _default_selected_ref(source) -> str | None:
    if isinstance(source, WorkingSaveModel):
        node_ids = source.ui.metadata.get("selected_node_ids")
        if isinstance(node_ids, list) and node_ids:
            return f"node:{node_ids[0]}"
    return None


def _find_validation_findings(validation_report: ValidationReport | None, target_id: str | None) -> list[FindingRefView]:
    if validation_report is None or not target_id:
        return []
    findings: list[FindingRefView] = []
    for finding in validation_report.findings:
        location = finding.location or ""
        if target_id in location or location.endswith(target_id):
            findings.append(FindingRefView(finding_type=finding.category, location_ref=finding.location, message=finding.message))
    return findings


def _find_execution_findings(execution_record: ExecutionRecordModel | None, target_id: str | None) -> list[FindingRefView]:
    if execution_record is None or not target_id:
        return []
    findings: list[FindingRefView] = []
    for issue in execution_record.diagnostics.errors:
        if target_id in (issue.location or ""):
            findings.append(FindingRefView(finding_type="error", location_ref=issue.location, message=issue.message))
    for issue in execution_record.diagnostics.warnings:
        if target_id in (issue.location or ""):
            findings.append(FindingRefView(finding_type="warning", location_ref=issue.location, message=issue.message))
    return findings


def _find_preview_changes(preview_overlay: GraphPreviewOverlay | None, target_ref: str | None) -> list[PreviewChangeRefView]:
    if preview_overlay is None or not target_ref:
        return []
    target_id = target_ref.split(":", 1)[1] if ":" in target_ref else target_ref
    changes: list[PreviewChangeRefView] = []
    if target_id in preview_overlay.added_node_ids:
        changes.append(PreviewChangeRefView(change_type="added", target_ref=target_ref, message="Added in preview"))
    if target_id in preview_overlay.updated_node_ids:
        changes.append(PreviewChangeRefView(change_type="updated", target_ref=target_ref, message="Updated in preview"))
    if target_id in preview_overlay.removed_node_ids:
        changes.append(PreviewChangeRefView(change_type="removed", target_ref=target_ref, message="Removed in preview"))
    if target_id in preview_overlay.affected_node_ids and not changes:
        changes.append(PreviewChangeRefView(change_type="affected", target_ref=target_ref, message="Affected by preview"))
    return changes


def _node_result_for(execution_record: ExecutionRecordModel | None, node_id: str | None) -> NodeResultCard | None:
    if execution_record is None or node_id is None:
        return None
    for result in execution_record.node_results.results:
        if result.node_id == node_id:
            return result
    return None


def _object_status(
    source,
    *,
    object_ref: str | None,
    validation_report: ValidationReport | None,
    execution_record: ExecutionRecordModel | None,
    preview_overlay: GraphPreviewOverlay | None,
) -> ObjectStatusSummary:
    storage_role = _storage_role(source)
    target_id = object_ref.split(":", 1)[1] if object_ref and ":" in object_ref else object_ref
    validation_state = "unknown"
    if validation_report is not None:
        related = _find_validation_findings(validation_report, target_id)
        if any(validation_report.findings and f.location_ref for f in related):
            validation_state = "blocked" if validation_report.blocking_count else "warning"
        elif validation_report.result == "passed":
            validation_state = "pass"
        elif validation_report.result == "passed_with_findings":
            validation_state = "warning"
        else:
            validation_state = "blocked"
    execution_state = None
    if object_ref and object_ref.startswith("node:"):
        result = _node_result_for(execution_record, target_id)
        if result is not None:
            execution_state = {
                "success": "completed",
                "failed": "failed",
                "warning": "partial",
            }.get(result.status, result.status)
        elif execution_record is not None and execution_record.meta.status == "running":
            execution_state = "running"
    preview_state = "none"
    if preview_overlay is not None and target_id is not None:
        if target_id in preview_overlay.added_node_ids:
            preview_state = "added"
        elif target_id in preview_overlay.updated_node_ids:
            preview_state = "updated"
        elif target_id in preview_overlay.removed_node_ids:
            preview_state = "removed"
        elif target_id in preview_overlay.affected_node_ids:
            preview_state = "affected"
    editability = "editable" if storage_role == "working_save" else "readonly"
    overall_status = "normal"
    short_label = None
    if storage_role == "execution_record":
        editability = "readonly"
    if execution_state == "failed":
        overall_status = "failed"
        short_label = "Execution failed"
    elif execution_state == "running":
        overall_status = "running"
        short_label = "Running"
    elif preview_state not in {None, "none"}:
        overall_status = "preview_changed"
        short_label = "Preview changed"
    elif validation_state == "blocked":
        overall_status = "blocked"
        short_label = "Blocked"
    elif validation_state == "warning":
        overall_status = "warning"
        short_label = "Warning"
    elif execution_state == "completed":
        overall_status = "completed"
        short_label = "Completed"
    if storage_role != "working_save" and overall_status == "normal":
        overall_status = "readonly"
        short_label = "Read-only"
    return ObjectStatusSummary(
        overall_status=overall_status,
        validation_state=validation_state,
        execution_state=execution_state,
        preview_state=preview_state,
        editability=editability,
        short_label=short_label,
    )


def _normalize_display(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        parts = [f"{key}={value[key]}" for key in sorted(value)[:4]]
        return ", ".join(parts)
    return str(value)


def _field_views_for_node(node: Mapping[str, Any], *, storage_role: str) -> tuple[list[EditableFieldView], list[ReadonlyFieldView], list[ConstraintView]]:
    editable: list[EditableFieldView] = []
    readonly: list[ReadonlyFieldView] = []
    constraints: list[ConstraintView] = []
    editable_allowed = storage_role == "working_save"
    readonly.append(ReadonlyFieldView("node_id", "Node ID", node.get("id"), display_value=_normalize_display(node.get("id")), reason_readonly="Stable object identity"))
    kind = node.get("kind") or node.get("type") or "unknown"
    readonly.append(ReadonlyFieldView("kind", "Kind", kind, display_value=_normalize_display(kind), reason_readonly="Derived from structural truth"))
    editable.append(
        EditableFieldView(
            field_key="label",
            label="Label",
            value=node.get("label"),
            display_value=_normalize_display(node.get("label")),
            mutable=editable_allowed,
            nullable=True,
            current_source="circuit.nodes[].label",
            change_scope="node_level",
        )
    )
    if "inputs" in node:
        editable.append(
            EditableFieldView(
                field_key="inputs",
                label="Inputs",
                value=node.get("inputs"),
                display_value=_normalize_display(node.get("inputs")),
                editor_type="json",
                mutable=editable_allowed,
                nullable=True,
                current_source="circuit.nodes[].inputs",
                change_scope="node_level",
            )
        )
    if "outputs" in node:
        editable.append(
            EditableFieldView(
                field_key="outputs",
                label="Outputs",
                value=node.get("outputs"),
                display_value=_normalize_display(node.get("outputs")),
                editor_type="json",
                mutable=editable_allowed,
                nullable=True,
                current_source="circuit.nodes[].outputs",
                change_scope="node_level",
            )
        )
    if kind == "subcircuit" or kind == "subcircuit_node":
        child_ref = (((node.get("execution") or {}).get("subcircuit") or {}).get("child_circuit_ref"))
        readonly.append(ReadonlyFieldView("child_circuit_ref", "Child Circuit", child_ref, display_value=_normalize_display(child_ref), reason_readonly="Bounded child circuit reference"))
        constraints.append(ConstraintView(label="Subcircuit boundary", message="Parent/child data exchange remains mapping-bound and read-only at runtime boundary."))
    return editable, readonly, constraints


def _field_views_for_edge(edge: Mapping[str, Any], *, storage_role: str) -> tuple[list[EditableFieldView], list[ReadonlyFieldView], list[ConstraintView]]:
    editable_allowed = storage_role == "working_save"
    readonly = [
        ReadonlyFieldView("from", "From", edge.get("from"), display_value=_normalize_display(edge.get("from")), reason_readonly="Graph endpoint"),
        ReadonlyFieldView("to", "To", edge.get("to"), display_value=_normalize_display(edge.get("to")), reason_readonly="Graph endpoint"),
    ]
    editable = [
        EditableFieldView(
            field_key="label",
            label="Label",
            value=edge.get("label"),
            display_value=_normalize_display(edge.get("label")),
            mutable=editable_allowed,
            nullable=True,
            change_scope="field_only",
        )
    ]
    return editable, readonly, []


def _field_views_for_output(output: Mapping[str, Any], *, storage_role: str) -> tuple[list[EditableFieldView], list[ReadonlyFieldView], list[ConstraintView]]:
    editable_allowed = storage_role == "working_save"
    editable = [
        EditableFieldView(
            field_key="name",
            label="Output Name",
            value=output.get("name"),
            display_value=_normalize_display(output.get("name")),
            mutable=editable_allowed,
            nullable=False,
            change_scope="field_only",
        )
    ]
    readonly = [ReadonlyFieldView("source", "Source", output.get("source"), display_value=_normalize_display(output.get("source")), reason_readonly="Derived output binding")]
    return editable, readonly, []


def read_selected_object_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    selected_ref: str | None = None,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    explanation: str | None = None,
) -> SelectedObjectViewModel:
    source = _unwrap(source)
    storage_role = _storage_role(source)
    selected_ref = selected_ref or _default_selected_ref(source)
    if selected_ref is None:
        return SelectedObjectViewModel(
            object_type="none",
            object_id=None,
            storage_role=storage_role,
            title="Nothing selected",
            status_summary=ObjectStatusSummary(overall_status="unknown", editability="unknown"),
            empty_state_message="Select a node, edge, output, or group to inspect details.",
            explanation=explanation,
        )
    prefix, _, target_id = selected_ref.partition(":")
    circuit = _circuit_from_source(source)
    editable_fields: list[EditableFieldView] = []
    readonly_fields: list[ReadonlyFieldView] = []
    constraints: list[ConstraintView] = []
    title = target_id or selected_ref
    subtitle = None
    description = None
    object_type = prefix if prefix else "unknown"

    if circuit is not None and object_type == "node":
        node = next((node for node in circuit.nodes if node.get("id") == target_id), None)
        if node is not None:
            editable_fields, readonly_fields, constraints = _field_views_for_node(node, storage_role=storage_role)
            title = node.get("label") or target_id
            subtitle = str(node.get("kind") or node.get("type") or "node")
            description = f"Node {target_id}"
    elif circuit is not None and object_type == "edge":
        parts = target_id.split("->")
        edge = None
        for candidate in circuit.edges:
            edge_ref = f"{candidate.get('from')}->{candidate.get('to')}"
            if edge_ref == target_id:
                edge = candidate
                break
        if edge is not None:
            editable_fields, readonly_fields, constraints = _field_views_for_edge(edge, storage_role=storage_role)
            title = edge.get("label") or target_id
            subtitle = "edge"
            description = f"Edge {target_id}"
    elif circuit is not None and object_type == "output":
        output = next((item for item in circuit.outputs if item.get("name") == target_id), None)
        if output is not None:
            editable_fields, readonly_fields, constraints = _field_views_for_output(output, storage_role=storage_role)
            title = output.get("name") or target_id
            subtitle = "output"
            description = f"Output {target_id}"
    elif circuit is not None and object_type == "subcircuit":
        subcircuit = (circuit.subcircuits or {}).get(target_id)
        if subcircuit is not None:
            title = target_id
            subtitle = "subcircuit"
            description = "Referenced child circuit"
            readonly_fields = [
                ReadonlyFieldView("node_count", "Node Count", len(subcircuit.get("nodes", [])), display_value=str(len(subcircuit.get("nodes", []))), reason_readonly="Derived child circuit size"),
                ReadonlyFieldView("edge_count", "Edge Count", len(subcircuit.get("edges", [])), display_value=str(len(subcircuit.get("edges", []))), reason_readonly="Derived child circuit size"),
            ]
            constraints = [ConstraintView(label="Nested execution", message="Subcircuits remain wrapped by a node-kind boundary and are not top-level runtime units.")]
    status_summary = _object_status(
        source,
        object_ref=selected_ref,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
    )
    validation_refs = _find_validation_findings(validation_report, target_id)
    execution_refs = _find_execution_findings(execution_record, target_id)
    preview_refs = _find_preview_changes(preview_overlay, selected_ref)
    warnings = [InlineWarningView(code="validation", severity="warning", message=ref.message) for ref in validation_refs[:3]]
    related_actions = [
        InspectorActionHint("focus_in_graph", "Focus in graph", True),
        InspectorActionHint(
            "edit_selection",
            "Edit selection",
            status_summary.editability == "editable",
            None if status_summary.editability == "editable" else "Selection is read-only in this storage role",
        ),
    ]
    return SelectedObjectViewModel(
        object_type=object_type if object_type else "unknown",
        object_id=target_id or None,
        storage_role=storage_role,
        title=title,
        subtitle=subtitle,
        description=description,
        status_summary=status_summary,
        editable_fields=editable_fields,
        readonly_fields=readonly_fields,
        warnings=warnings,
        constraints=constraints,
        related_validation_findings=validation_refs,
        related_execution_findings=execution_refs,
        related_preview_changes=preview_refs,
        related_actions=related_actions,
        explanation=explanation,
    )


__all__ = [
    "ConstraintView",
    "EditableFieldView",
    "FindingRefView",
    "InlineWarningView",
    "InspectorActionHint",
    "ObjectStatusSummary",
    "PreviewChangeRefView",
    "ReadonlyFieldView",
    "SelectedObjectViewModel",
    "read_selected_object_view_model",
]
