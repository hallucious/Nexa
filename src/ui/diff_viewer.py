from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay


@dataclass(frozen=True)
class DiffEndpointRefView:
    endpoint_type: str
    ref_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    status_label: str | None = None


@dataclass(frozen=True)
class DiffSummaryView:
    total_change_count: int = 0
    added_count: int = 0
    removed_count: int = 0
    updated_count: int = 0
    moved_count: int = 0
    destructive_change_count: int = 0
    structural_change_count: int = 0
    execution_change_count: int = 0
    artifact_change_count: int = 0
    top_summary_label: str | None = None


@dataclass(frozen=True)
class DiffChangeItemView:
    change_id: str
    change_type: str
    category: str
    target_type: str
    target_id: str | None
    short_label: str
    before_preview: str | None = None
    after_preview: str | None = None
    destructive: bool = False
    severity: str | None = None
    signal_type: str | None = None


@dataclass(frozen=True)
class DiffGroupView:
    group_id: str
    group_label: str
    group_type: str
    changes: list[DiffChangeItemView]
    count: int
    collapsed_by_default: bool = False


@dataclass(frozen=True)
class RawDiffOpView:
    op_type: str
    text_preview: str


@dataclass(frozen=True)
class DiffSignalView:
    signal_type: str
    before: str | None = None
    after: str | None = None
    confidence: float | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class DiffChangeDetailView:
    change_id: str
    title: str
    description: str | None = None
    category: str = "unknown"
    before_value_preview: str | None = None
    after_value_preview: str | None = None
    raw_diff_ops: list[RawDiffOpView] = field(default_factory=list)
    normalized_signals: list[DiffSignalView] = field(default_factory=list)
    affected_refs: list[str] = field(default_factory=list)
    related_finding_ids: list[str] = field(default_factory=list)
    related_event_ids: list[str] = field(default_factory=list)
    explanation: str | None = None


@dataclass(frozen=True)
class DiffFilterStateView:
    show_added: bool = True
    show_removed: bool = True
    show_updated: bool = True
    show_destructive_only: bool = False
    show_structural_only: bool = False
    show_execution_only: bool = False
    search_query: str | None = None
    group_by: str = "category"


@dataclass(frozen=True)
class DiffRelatedLinksView:
    related_graph_target_ids: list[str] = field(default_factory=list)
    related_inspector_target_ids: list[str] = field(default_factory=list)
    related_validation_finding_ids: list[str] = field(default_factory=list)
    related_run_ids: list[str] = field(default_factory=list)
    related_artifact_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DiffDiagnosticsView:
    incomplete_diff: bool = False
    missing_source_ref: bool = False
    missing_target_ref: bool = False
    unsupported_section_count: int = 0
    load_error_count: int = 0
    last_error_label: str | None = None


@dataclass(frozen=True)
class DiffViewerViewModel:
    diff_mode: str
    viewer_status: str
    source_ref: DiffEndpointRefView
    target_ref: DiffEndpointRefView
    summary: DiffSummaryView
    grouped_changes: list[DiffGroupView] = field(default_factory=list)
    selected_change: DiffChangeDetailView | None = None
    filter_state: DiffFilterStateView = field(default_factory=DiffFilterStateView)
    related_links: DiffRelatedLinksView = field(default_factory=DiffRelatedLinksView)
    diagnostics: DiffDiagnosticsView = field(default_factory=DiffDiagnosticsView)
    explanation: str | None = None


@dataclass(frozen=True)
class _DiffChange:
    change_id: str
    change_type: str
    category: str
    target_type: str
    target_id: str | None
    short_label: str
    before_preview: str | None
    after_preview: str | None
    destructive: bool
    severity: str | None
    signal_type: str | None
    affected_refs: list[str]
    related_run_ids: list[str] = field(default_factory=list)
    related_artifact_ids: list[str] = field(default_factory=list)



def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source



def _to_preview(value: Any) -> str | None:
    if value is None:
        return None
    text = repr(value)
    return text if len(text) <= 120 else text[:117] + "..."



def _node_map(circuit) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for index, node in enumerate(circuit.nodes):
        if isinstance(node, Mapping):
            node_id = str(node.get("id") or node.get("node_id") or f"node_{index}")
            result[node_id] = node
    return result



def _edge_map(circuit) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for index, edge in enumerate(circuit.edges):
        if isinstance(edge, Mapping):
            from_node = edge.get("from") or edge.get("from_node_id") or edge.get("source") or "unknown"
            to_node = edge.get("to") or edge.get("to_node_id") or edge.get("target") or "unknown"
            edge_id = str(edge.get("id") or edge.get("edge_id") or f"edge_{index}:{from_node}->{to_node}")
            result[edge_id] = edge
    return result



def _make_change(
    *,
    change_id: str,
    change_type: str,
    category: str,
    target_type: str,
    target_id: str | None,
    short_label: str,
    before: Any,
    after: Any,
    destructive: bool = False,
    severity: str | None = None,
    signal_type: str | None = None,
    related_run_ids: Iterable[str] | None = None,
    related_artifact_ids: Iterable[str] | None = None,
) -> _DiffChange:
    return _DiffChange(
        change_id=change_id,
        change_type=change_type,
        category=category,
        target_type=target_type,
        target_id=target_id,
        short_label=short_label,
        before_preview=_to_preview(before),
        after_preview=_to_preview(after),
        destructive=destructive,
        severity=severity,
        signal_type=signal_type,
        affected_refs=[target_id] if target_id else [],
        related_run_ids=list(related_run_ids or []),
        related_artifact_ids=list(related_artifact_ids or []),
    )



def _compare_circuits(source: WorkingSaveModel | CommitSnapshotModel, target: CommitSnapshotModel) -> list[_DiffChange]:
    changes: list[_DiffChange] = []
    source_nodes = _node_map(source.circuit)
    target_nodes = _node_map(target.circuit)
    for node_id in sorted(set(source_nodes) | set(target_nodes)):
        s = source_nodes.get(node_id)
        t = target_nodes.get(node_id)
        if s is None:
            changes.append(_make_change(change_id=f"node:add:{node_id}", change_type="added", category="node", target_type="node", target_id=node_id, short_label=f"Node {node_id} added", before=None, after=t, signal_type="ADD"))
        elif t is None:
            changes.append(_make_change(change_id=f"node:remove:{node_id}", change_type="removed", category="node", target_type="node", target_id=node_id, short_label=f"Node {node_id} removed", before=s, after=None, destructive=True, severity="warning", signal_type="REMOVE"))
        elif s != t:
            changes.append(_make_change(change_id=f"node:update:{node_id}", change_type="updated", category="node", target_type="node", target_id=node_id, short_label=f"Node {node_id} updated", before=s, after=t, severity="info", signal_type="MODIFY"))

    source_edges = _edge_map(source.circuit)
    target_edges = _edge_map(target.circuit)
    for edge_id in sorted(set(source_edges) | set(target_edges)):
        s = source_edges.get(edge_id)
        t = target_edges.get(edge_id)
        if s is None:
            changes.append(_make_change(change_id=f"edge:add:{edge_id}", change_type="added", category="edge", target_type="edge", target_id=edge_id, short_label=f"Edge {edge_id} added", before=None, after=t, signal_type="ADD"))
        elif t is None:
            changes.append(_make_change(change_id=f"edge:remove:{edge_id}", change_type="removed", category="edge", target_type="edge", target_id=edge_id, short_label=f"Edge {edge_id} removed", before=s, after=None, destructive=True, severity="warning", signal_type="REMOVE"))
        elif s != t:
            changes.append(_make_change(change_id=f"edge:update:{edge_id}", change_type="updated", category="edge", target_type="edge", target_id=edge_id, short_label=f"Edge {edge_id} updated", before=s, after=t, severity="info", signal_type="MODIFY"))

    if source.resources != target.resources:
        changes.append(_make_change(change_id="resources:update", change_type="updated", category="resource", target_type="storage", target_id="resources", short_label="Resources changed", before=source.resources, after=target.resources, severity="info", signal_type="MODIFY"))
    if source.circuit.outputs != target.circuit.outputs:
        changes.append(_make_change(change_id="outputs:update", change_type="updated", category="output", target_type="output", target_id="outputs", short_label="Outputs changed", before=source.circuit.outputs, after=target.circuit.outputs, severity="info", signal_type="MODIFY"))
    return changes



def _compare_runs(source: ExecutionRecordModel, target: ExecutionRecordModel) -> list[_DiffChange]:
    changes: list[_DiffChange] = []
    source_results = {card.node_id: card for card in source.node_results.results}
    target_results = {card.node_id: card for card in target.node_results.results}
    for node_id in sorted(set(source_results) | set(target_results)):
        s = source_results.get(node_id)
        t = target_results.get(node_id)
        if s is None:
            changes.append(_make_change(change_id=f"run:add:{node_id}", change_type="added", category="execution_result", target_type="run", target_id=node_id, short_label=f"Node result {node_id} added", before=None, after=t.status if t else None, signal_type="ADD", related_run_ids=[source.meta.run_id, target.meta.run_id]))
        elif t is None:
            changes.append(_make_change(change_id=f"run:remove:{node_id}", change_type="removed", category="execution_result", target_type="run", target_id=node_id, short_label=f"Node result {node_id} removed", before=s.status if s else None, after=None, destructive=True, severity="warning", signal_type="REMOVE", related_run_ids=[source.meta.run_id, target.meta.run_id]))
        elif (s.status, s.output_summary) != (t.status, t.output_summary):
            changes.append(_make_change(change_id=f"run:update:{node_id}", change_type="updated", category="execution_result", target_type="run", target_id=node_id, short_label=f"Node result {node_id} changed", before={"status": s.status, "output": s.output_summary}, after={"status": t.status, "output": t.output_summary}, severity="info", signal_type="MODIFY", related_run_ids=[source.meta.run_id, target.meta.run_id]))

    source_artifacts = {artifact.artifact_id for artifact in source.artifacts.artifact_refs}
    target_artifacts = {artifact.artifact_id for artifact in target.artifacts.artifact_refs}
    for artifact_id in sorted(source_artifacts ^ target_artifacts):
        change_type = "added" if artifact_id in target_artifacts else "removed"
        changes.append(_make_change(change_id=f"artifact:{change_type}:{artifact_id}", change_type=change_type, category="artifact", target_type="artifact", target_id=artifact_id, short_label=f"Artifact {artifact_id} {change_type}", before=artifact_id if change_type == "removed" else None, after=artifact_id if change_type == "added" else None, destructive=change_type == "removed", severity="info", signal_type="ADD" if change_type == "added" else "REMOVE", related_run_ids=[source.meta.run_id, target.meta.run_id], related_artifact_ids=[artifact_id]))

    if source.outputs.output_summary != target.outputs.output_summary:
        changes.append(_make_change(change_id="run:outputs:update", change_type="updated", category="execution_result", target_type="run", target_id="outputs", short_label="Run output summary changed", before=source.outputs.output_summary, after=target.outputs.output_summary, severity="info", signal_type="MODIFY", related_run_ids=[source.meta.run_id, target.meta.run_id]))
    return changes



def _changes_from_preview(preview_overlay: GraphPreviewOverlay) -> list[_DiffChange]:
    changes: list[_DiffChange] = []
    for node_id in preview_overlay.added_node_ids:
        changes.append(_make_change(change_id=f"preview:add:{node_id}", change_type="added", category="node", target_type="preview", target_id=node_id, short_label=f"Preview adds node {node_id}", before=None, after=node_id, signal_type="ADD"))
    for node_id in preview_overlay.updated_node_ids:
        changes.append(_make_change(change_id=f"preview:update:{node_id}", change_type="updated", category="node", target_type="preview", target_id=node_id, short_label=f"Preview updates node {node_id}", before=node_id, after=node_id, severity="info", signal_type="MODIFY"))
    for node_id in preview_overlay.removed_node_ids:
        changes.append(_make_change(change_id=f"preview:remove:{node_id}", change_type="removed", category="node", target_type="preview", target_id=node_id, short_label=f"Preview removes node {node_id}", before=node_id, after=None, destructive=True, severity="warning", signal_type="REMOVE"))
    for edge_id in preview_overlay.added_edge_ids:
        changes.append(_make_change(change_id=f"preview:edge:add:{edge_id}", change_type="added", category="edge", target_type="preview", target_id=edge_id, short_label=f"Preview adds edge {edge_id}", before=None, after=edge_id, signal_type="ADD"))
    for edge_id in preview_overlay.removed_edge_ids:
        changes.append(_make_change(change_id=f"preview:edge:remove:{edge_id}", change_type="removed", category="edge", target_type="preview", target_id=edge_id, short_label=f"Preview removes edge {edge_id}", before=edge_id, after=None, destructive=True, severity="warning", signal_type="REMOVE"))
    return changes



def _endpoint_ref(source: Any, *, fallback_type: str = "unknown") -> DiffEndpointRefView:
    source = _unwrap(source)
    if isinstance(source, WorkingSaveModel):
        return DiffEndpointRefView(endpoint_type="working_save", ref_id=f"working_save:{source.meta.working_save_id}", title=source.meta.name, created_at=source.meta.updated_at or source.meta.created_at, status_label=str(source.runtime.status))
    if isinstance(source, CommitSnapshotModel):
        return DiffEndpointRefView(endpoint_type="commit_snapshot", ref_id=f"commit_snapshot:{source.meta.commit_id}", title=source.meta.name, created_at=source.meta.updated_at or source.meta.created_at, status_label=source.approval.approval_status or source.validation.validation_result)
    if isinstance(source, ExecutionRecordModel):
        return DiffEndpointRefView(endpoint_type="execution_record", ref_id=f"execution_record:{source.meta.run_id}", title=source.meta.title, created_at=source.meta.created_at, status_label=source.meta.status)
    if isinstance(source, GraphPreviewOverlay):
        return DiffEndpointRefView(endpoint_type="preview", ref_id=source.overlay_id, title=source.summary, status_label="preview")
    return DiffEndpointRefView(endpoint_type=fallback_type)



def _group_changes(changes: Sequence[_DiffChange]) -> list[DiffGroupView]:
    by_category: dict[str, list[DiffChangeItemView]] = {}
    for change in changes:
        item = DiffChangeItemView(
            change_id=change.change_id,
            change_type=change.change_type,
            category=change.category,
            target_type=change.target_type,
            target_id=change.target_id,
            short_label=change.short_label,
            before_preview=change.before_preview,
            after_preview=change.after_preview,
            destructive=change.destructive,
            severity=change.severity,
            signal_type=change.signal_type,
        )
        by_category.setdefault(change.category, []).append(item)
    return [
        DiffGroupView(group_id=f"category:{category}", group_label=category.replace("_", " ").title(), group_type="category", changes=items, count=len(items))
        for category, items in sorted(by_category.items())
    ]



def _summary(changes: Sequence[_DiffChange], *, diff_mode: str) -> DiffSummaryView:
    added_count = sum(1 for c in changes if c.change_type == "added")
    removed_count = sum(1 for c in changes if c.change_type == "removed")
    updated_count = sum(1 for c in changes if c.change_type == "updated")
    moved_count = sum(1 for c in changes if c.change_type == "moved")
    destructive_change_count = sum(1 for c in changes if c.destructive)
    structural_change_count = sum(1 for c in changes if c.category in {"node", "edge", "resource", "output", "parameter"})
    execution_change_count = sum(1 for c in changes if c.category == "execution_result")
    artifact_change_count = sum(1 for c in changes if c.category == "artifact")
    return DiffSummaryView(
        total_change_count=len(changes),
        added_count=added_count,
        removed_count=removed_count,
        updated_count=updated_count,
        moved_count=moved_count,
        destructive_change_count=destructive_change_count,
        structural_change_count=structural_change_count,
        execution_change_count=execution_change_count,
        artifact_change_count=artifact_change_count,
        top_summary_label=f"{len(changes)} changes in {diff_mode}",
    )



def _selected_change(changes: Sequence[_DiffChange]) -> DiffChangeDetailView | None:
    if not changes:
        return None
    change = changes[0]
    raw_ops: list[RawDiffOpView] = []
    if change.before_preview is not None:
        raw_ops.append(RawDiffOpView(op_type="delete", text_preview=change.before_preview))
    if change.after_preview is not None:
        raw_ops.append(RawDiffOpView(op_type="insert", text_preview=change.after_preview))
    signals = [
        DiffSignalView(
            signal_type=change.signal_type or change.change_type.upper(),
            before=change.before_preview,
            after=change.after_preview,
            confidence=1.0,
            explanation=change.short_label,
        )
    ]
    return DiffChangeDetailView(
        change_id=change.change_id,
        title=change.short_label,
        category=change.category,
        before_value_preview=change.before_preview,
        after_value_preview=change.after_preview,
        raw_diff_ops=raw_ops,
        normalized_signals=signals,
        affected_refs=change.affected_refs,
        related_event_ids=change.related_run_ids,
        explanation=change.short_label,
    )



def _related_links(changes: Sequence[_DiffChange]) -> DiffRelatedLinksView:
    graph_targets: list[str] = []
    run_ids: list[str] = []
    artifact_ids: list[str] = []
    for change in changes:
        if change.target_id:
            graph_targets.append(change.target_id)
        run_ids.extend(change.related_run_ids)
        artifact_ids.extend(change.related_artifact_ids)
    return DiffRelatedLinksView(
        related_graph_target_ids=sorted(set(graph_targets)),
        related_inspector_target_ids=sorted(set(graph_targets)),
        related_run_ids=sorted(set(run_ids)),
        related_artifact_ids=sorted(set(artifact_ids)),
    )



def read_diff_view_model(
    *,
    diff_mode: str,
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | GraphPreviewOverlay | None,
    target: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | GraphPreviewOverlay | None,
    explanation: str | None = None,
) -> DiffViewerViewModel:
    """Build a UI-facing diff projection from explicit comparison endpoints."""

    source_unwrapped = _unwrap(source)
    target_unwrapped = _unwrap(target)
    diagnostics = DiffDiagnosticsView(
        missing_source_ref=source_unwrapped is None and not isinstance(source, GraphPreviewOverlay),
        missing_target_ref=target_unwrapped is None and not isinstance(target, GraphPreviewOverlay),
    )
    if diagnostics.missing_source_ref or diagnostics.missing_target_ref:
        return DiffViewerViewModel(
            diff_mode=diff_mode,
            viewer_status="failed",
            source_ref=_endpoint_ref(source_unwrapped, fallback_type="unknown"),
            target_ref=_endpoint_ref(target_unwrapped, fallback_type="unknown"),
            summary=DiffSummaryView(top_summary_label="Comparison endpoints are incomplete"),
            diagnostics=diagnostics,
            explanation=explanation,
        )

    changes: list[_DiffChange]
    if diff_mode == "draft_vs_commit" and isinstance(source_unwrapped, WorkingSaveModel) and isinstance(target_unwrapped, CommitSnapshotModel):
        changes = _compare_circuits(source_unwrapped, target_unwrapped)
    elif diff_mode == "run_vs_run" and isinstance(source_unwrapped, ExecutionRecordModel) and isinstance(target_unwrapped, ExecutionRecordModel):
        changes = _compare_runs(source_unwrapped, target_unwrapped)
    elif diff_mode == "preview_vs_current" and isinstance(source, GraphPreviewOverlay) and isinstance(target_unwrapped, (WorkingSaveModel, CommitSnapshotModel)):
        changes = _changes_from_preview(source)
    elif diff_mode == "commit_vs_commit" and isinstance(source_unwrapped, CommitSnapshotModel) and isinstance(target_unwrapped, CommitSnapshotModel):
        changes = _compare_circuits(source_unwrapped, target_unwrapped)
    else:
        changes = []
        diagnostics = DiffDiagnosticsView(incomplete_diff=True, unsupported_section_count=1, last_error_label=f"Unsupported diff mode/endpoints: {diff_mode}")

    viewer_status = "ready" if changes or diagnostics.unsupported_section_count == 0 else "partial"
    if diagnostics.unsupported_section_count:
        viewer_status = "partial"

    return DiffViewerViewModel(
        diff_mode=diff_mode,
        viewer_status=viewer_status,
        source_ref=_endpoint_ref(source, fallback_type="unknown"),
        target_ref=_endpoint_ref(target, fallback_type="unknown"),
        summary=_summary(changes, diff_mode=diff_mode),
        grouped_changes=_group_changes(changes),
        selected_change=_selected_change(changes),
        filter_state=DiffFilterStateView(),
        related_links=_related_links(changes),
        diagnostics=diagnostics,
        explanation=explanation,
    )


__all__ = [
    "DiffEndpointRefView",
    "DiffSummaryView",
    "DiffGroupView",
    "DiffChangeItemView",
    "DiffChangeDetailView",
    "RawDiffOpView",
    "DiffSignalView",
    "DiffFilterStateView",
    "DiffRelatedLinksView",
    "DiffDiagnosticsView",
    "DiffViewerViewModel",
    "read_diff_view_model",
]
