from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel, NodeResultCard, NodeTimingCard
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text

GraphStorageRole = str
GraphStatus = str
NodeStatus = str
ExecutionState = str
ValidationState = str
PreviewChangeState = str


@dataclass(frozen=True)
class NodePosition:
    x: float
    y: float


@dataclass(frozen=True)
class NodeSize:
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class NodeBadgeView:
    badge_type: str
    label: str
    severity: str | None = None
    count: int | None = None


@dataclass(frozen=True)
class GraphNodeView:
    node_id: str
    label: str
    kind: str
    subtype: str | None = None
    position: NodePosition | None = None
    size: NodeSize | None = None
    status: NodeStatus = "unknown"
    execution_state: ExecutionState | None = None
    validation_state: ValidationState | None = None
    title_badge: str | None = None
    badges: list[NodeBadgeView] = field(default_factory=list)
    input_summary: str | None = None
    output_summary: str | None = None
    preview_change_state: PreviewChangeState = "unchanged"
    has_designer_proposal: bool = False
    has_blocking_findings: bool = False
    has_warning_findings: bool = False
    has_execution_events: bool = False
    child_refs: list[str] | None = None
    metadata_summary: dict[str, Any] | None = None


@dataclass(frozen=True)
class GraphEdgeView:
    edge_id: str
    from_node_id: str
    to_node_id: str
    label: str | None = None
    status: str = "normal"
    edge_type: str | None = None
    preview_change_state: str = "unchanged"
    metadata_summary: dict[str, Any] | None = None


@dataclass(frozen=True)
class GraphGroupView:
    group_id: str
    label: str
    member_node_ids: list[str]
    collapsed: bool = False
    status: str | None = None
    metadata_summary: dict[str, Any] | None = None


@dataclass(frozen=True)
class GraphMetricsView:
    node_count: int = 0
    edge_count: int = 0
    group_count: int = 0
    warning_count: int = 0
    blocking_count: int = 0
    running_node_count: int = 0
    completed_node_count: int = 0
    failed_node_count: int = 0
    preview_added_count: int = 0
    preview_updated_count: int = 0
    preview_removed_count: int = 0


@dataclass(frozen=True)
class GraphFindingsSummary:
    validation_warning_count: int = 0
    validation_blocking_count: int = 0
    confirmation_required_count: int = 0
    execution_warning_count: int = 0
    execution_error_count: int = 0
    designer_pending_count: int = 0


@dataclass(frozen=True)
class GraphPreviewOverlay:
    overlay_id: str
    preview_ref: str | None = None
    summary: str = ""
    affected_node_ids: list[str] = field(default_factory=list)
    affected_edge_ids: list[str] = field(default_factory=list)
    added_node_ids: list[str] = field(default_factory=list)
    updated_node_ids: list[str] = field(default_factory=list)
    removed_node_ids: list[str] = field(default_factory=list)
    added_edge_ids: list[str] = field(default_factory=list)
    removed_edge_ids: list[str] = field(default_factory=list)
    destructive_change_present: bool = False
    requires_confirmation: bool = False


@dataclass(frozen=True)
class GraphLayoutHints:
    layout_mode: str | None = None
    suggested_focus_node_id: str | None = None
    suggested_zoom_region: dict[str, Any] | None = None
    minimap_enabled: bool | None = None


@dataclass(frozen=True)
class GraphWorkspaceViewModel:
    graph_id: str
    graph_title: str | None
    storage_role: GraphStorageRole
    graph_status: GraphStatus
    nodes: list[GraphNodeView]
    edges: list[GraphEdgeView]
    groups: list[GraphGroupView]
    selected_node_ids: list[str] = field(default_factory=list)
    selected_edge_ids: list[str] = field(default_factory=list)
    graph_metrics: GraphMetricsView = field(default_factory=GraphMetricsView)
    graph_findings_summary: GraphFindingsSummary = field(default_factory=GraphFindingsSummary)
    preview_overlay: GraphPreviewOverlay | None = None
    layout_hints: GraphLayoutHints | None = None
    explanation: str | None = None


def _node_id(node: Mapping[str, Any], fallback: int) -> str:
    return str(node.get("id") or node.get("node_id") or f"node_{fallback}")


def _node_label(node: Mapping[str, Any], *, node_id: str) -> str:
    return str(node.get("label") or node.get("name") or node_id)


def _node_kind(node: Mapping[str, Any]) -> str:
    return str(node.get("kind") or node.get("type") or "unknown")


def _resource_subtype(node: Mapping[str, Any]) -> str | None:
    resource_ref = node.get("resource_ref")
    if isinstance(resource_ref, Mapping):
        for key in ("provider", "plugin", "prompt"):
            value = resource_ref.get(key)
            if value:
                return str(value)
    execution = node.get("execution")
    if isinstance(execution, Mapping):
        for key in ("provider", "plugin", "prompt", "subcircuit"):
            if key in execution:
                if key == "subcircuit":
                    sub = execution.get("subcircuit")
                    if isinstance(sub, Mapping) and sub.get("child_circuit_ref"):
                        return str(sub.get("child_circuit_ref"))
                return key
    return None


def _node_position(node: Mapping[str, Any]) -> NodePosition | None:
    metadata = node.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    position = metadata.get("position")
    if isinstance(position, Mapping) and isinstance(position.get("x"), (int, float)) and isinstance(position.get("y"), (int, float)):
        return NodePosition(x=float(position["x"]), y=float(position["y"]))
    return None


def _node_size(node: Mapping[str, Any]) -> NodeSize | None:
    metadata = node.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    size = metadata.get("size")
    if isinstance(size, Mapping):
        width = size.get("width")
        height = size.get("height")
        if isinstance(width, (int, float)) or isinstance(height, (int, float)):
            return NodeSize(
                width=float(width) if isinstance(width, (int, float)) else None,
                height=float(height) if isinstance(height, (int, float)) else None,
            )
    return None


def _child_refs(node: Mapping[str, Any]) -> list[str] | None:
    execution = node.get("execution")
    if isinstance(execution, Mapping):
        sub = execution.get("subcircuit")
        if isinstance(sub, Mapping) and sub.get("child_circuit_ref"):
            return [str(sub["child_circuit_ref"])]
    return None


def _input_output_summary(node: Mapping[str, Any], *, key: str, app_language: str) -> str | None:
    value = node.get(key)
    if isinstance(value, Mapping):
        count = len(value)
        if count == 0:
            return None
        if count == 1:
            return ui_text("graph.binding.single", app_language=app_language, fallback_text="{count} binding", count=count)
        return ui_text("graph.binding.multiple", app_language=app_language, fallback_text="{count} bindings", count=count)
    return None


def _derive_edge_id(edge: Mapping[str, Any], index: int, *, from_node: str, to_node: str) -> str:
    return str(edge.get("id") or edge.get("edge_id") or f"edge_{index}:{from_node}->{to_node}")


def _edge_endpoint(edge: Mapping[str, Any], *names: str) -> str | None:
    for name in names:
        value = edge.get(name)
        if isinstance(value, str) and value:
            return value
    return None




def _preferred_execution_focus_node(record: ExecutionRecordModel | None) -> str | None:
    if record is None:
        return None
    for result in record.node_results.results:
        if result.status == "failed":
            return result.node_id
    for issue in [*record.diagnostics.errors, *record.diagnostics.warnings]:
        location = issue.location or ""
        if location.startswith("node:"):
            return location.split(":", 1)[1]
    for started in record.timeline.started_nodes:
        if started.outcome == "running":
            return started.node_id
    for result in record.node_results.results:
        if result.status in {"warning", "partial"}:
            return result.node_id
    for artifact in record.artifacts.artifact_refs:
        if artifact.producer_node:
            return artifact.producer_node
    if record.node_results.results:
        return record.node_results.results[0].node_id
    if record.timeline.started_nodes:
        return record.timeline.started_nodes[0].node_id
    return None

def _selection_from_working_save(source: WorkingSaveModel) -> tuple[list[str], list[str]]:
    metadata = source.ui.metadata or {}
    selected_nodes = metadata.get("selected_node_ids")
    selected_edges = metadata.get("selected_edge_ids")
    return (
        [str(v) for v in selected_nodes] if isinstance(selected_nodes, list) else [],
        [str(v) for v in selected_edges] if isinstance(selected_edges, list) else [],
    )


def _normalize_validation_report(report: ValidationReport | None) -> tuple[dict[str, list[Any]], GraphFindingsSummary]:
    if report is None:
        return {}, GraphFindingsSummary()
    by_location: dict[str, list[Any]] = {}
    for finding in report.findings:
        if finding.location:
            by_location.setdefault(str(finding.location), []).append(finding)
    confirmation_required_count = sum(1 for finding in report.findings if (not finding.blocking and finding.severity == "high"))
    summary = GraphFindingsSummary(
        validation_warning_count=report.warning_count,
        validation_blocking_count=report.blocking_count,
        confirmation_required_count=confirmation_required_count,
    )
    return by_location, summary


def _execution_maps(record: ExecutionRecordModel | None, *, app_language: str) -> tuple[dict[str, str], dict[str, list[NodeBadgeView]], GraphFindingsSummary]:
    if record is None:
        return {}, {}, GraphFindingsSummary()

    statuses: dict[str, str] = {}
    badges: dict[str, list[NodeBadgeView]] = {}

    def _append_badge(node_id: str, badge: NodeBadgeView) -> None:
        badges.setdefault(node_id, []).append(badge)

    for card in record.timeline.started_nodes:
        if card.outcome == "running":
            statuses[card.node_id] = "running"
            _append_badge(card.node_id, NodeBadgeView("execution_running", ui_text("graph.badge.running", app_language=app_language, fallback_text="Running"), severity="info"))

    for result in record.node_results.results:
        statuses[result.node_id] = result.status
        if result.status == "failed":
            _append_badge(result.node_id, NodeBadgeView("execution_failed", ui_text("graph.badge.failed", app_language=app_language, fallback_text="Failed"), severity="error", count=max(1, result.error_count)))
        elif result.status == "completed" or result.status == "success":
            _append_badge(result.node_id, NodeBadgeView("execution_completed", ui_text("graph.badge.completed", app_language=app_language, fallback_text="Completed"), severity="info"))
        elif result.status == "partial":
            _append_badge(result.node_id, NodeBadgeView("execution_completed", ui_text("graph.badge.partial", app_language=app_language, fallback_text="Partial"), severity="warning"))
        if result.warning_count:
            _append_badge(result.node_id, NodeBadgeView("validation_warning", ui_text("graph.badge.warnings", app_language=app_language, fallback_text="Warnings"), severity="warning", count=result.warning_count))

    findings = GraphFindingsSummary(
        execution_warning_count=len(record.diagnostics.warnings),
        execution_error_count=len(record.diagnostics.errors),
    )
    return statuses, badges, findings


def _node_preview_state(node_id: str, preview_overlay: GraphPreviewOverlay | None) -> str:
    if preview_overlay is None:
        return "unchanged"
    if node_id in preview_overlay.removed_node_ids:
        return "removed"
    if node_id in preview_overlay.added_node_ids:
        return "added"
    if node_id in preview_overlay.updated_node_ids:
        return "updated"
    if node_id in preview_overlay.affected_node_ids:
        return "affected"
    return "unchanged"


def _project_visual_status(*, preview_state: str, has_blocking: bool, execution_state: str | None, has_warning: bool) -> str:
    if preview_state == "removed":
        return "preview_removed"
    if has_blocking:
        return "blocked"
    if execution_state == "failed":
        return "failed"
    if execution_state == "running":
        return "running"
    if has_warning:
        return "warning"
    if preview_state == "updated":
        return "preview_updated"
    if preview_state == "added":
        return "preview_added"
    if execution_state in {"completed", "success"}:
        return "completed"
    return "normal"


def _build_node_metadata_summary(node: Mapping[str, Any]) -> dict[str, Any] | None:
    summary: dict[str, Any] = {}
    if node.get("resource_ref"):
        summary["resource_ref"] = node.get("resource_ref")
    if node.get("execution"):
        execution = node.get("execution")
        if isinstance(execution, Mapping):
            summary["execution_keys"] = sorted(str(k) for k in execution.keys())
    return summary or None


def _graph_status_for_source(
    source: WorkingSaveModel | CommitSnapshotModel,
    *,
    validation_report: ValidationReport | None,
    execution_record: ExecutionRecordModel | None,
) -> tuple[str, str]:
    if execution_record is not None:
        status = execution_record.meta.status
        mapped = {
            "running": "running",
            "completed": "completed",
            "failed": "failed",
            "partial": "partial",
            "cancelled": "failed",
        }.get(status, "unknown")
        return "execution_record", mapped

    if isinstance(source, WorkingSaveModel):
        runtime_status = str(source.runtime.status or "draft")
        if validation_report is not None and validation_report.blocking_count:
            return "working_save", "invalid"
        if runtime_status in {"review_ready", "validated"}:
            return "working_save", "review_ready"
        if runtime_status in {"running", "completed", "failed", "partial"}:
            return "working_save", runtime_status
        return "working_save", "draft"

    if isinstance(source, CommitSnapshotModel):
        if source.approval.approval_completed:
            return "commit_snapshot", "approved"
        return "commit_snapshot", "unknown"

    return "none", "unknown"


def read_graph_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | LoadedNexArtifact,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    selected_node_ids: Sequence[str] | None = None,
    selected_edge_ids: Sequence[str] | None = None,
    layout_hints: GraphLayoutHints | None = None,
    explanation: str | None = None,
) -> GraphWorkspaceViewModel:
    """Build a UI-facing graph projection from engine/storage truth.

    This is the minimal code-backed foundation for the Phase 5 Circuit Builder
    read-side contract. It remains read-only and keeps structural truth owned by
    the engine/storage layer.
    """

    if isinstance(source, LoadedNexArtifact):
        if source.parsed_model is None:
            raise ValueError("LoadedNexArtifact.parsed_model must be present to build a graph view")
        source = source.parsed_model

    resolved_selected_nodes: list[str]
    resolved_selected_edges: list[str]
    if selected_node_ids is not None or selected_edge_ids is not None:
        resolved_selected_nodes = [str(v) for v in (selected_node_ids or [])]
        resolved_selected_edges = [str(v) for v in (selected_edge_ids or [])]
    elif isinstance(source, WorkingSaveModel):
        resolved_selected_nodes, resolved_selected_edges = _selection_from_working_save(source)
    else:
        focus_node = _preferred_execution_focus_node(execution_record)
        resolved_selected_nodes = [focus_node] if focus_node else []
        resolved_selected_edges = []

    app_language = ui_language_from_sources(source, execution_record)
    validation_by_location, validation_summary = _normalize_validation_report(validation_report)
    execution_status_map, execution_badges, execution_summary = _execution_maps(execution_record, app_language=app_language)
    storage_role, graph_status = _graph_status_for_source(
        source,
        validation_report=validation_report,
        execution_record=execution_record,
    )

    nodes: list[GraphNodeView] = []
    for index, node in enumerate(source.circuit.nodes):
        if not isinstance(node, Mapping):
            continue
        node_id = _node_id(node, index)
        node_findings = validation_by_location.get(f"circuit.nodes[{index}]", []) + validation_by_location.get(node_id, [])
        has_blocking = any(f.blocking for f in node_findings)
        has_warning = any(not f.blocking for f in node_findings)
        preview_state = _node_preview_state(node_id, preview_overlay)
        execution_state = execution_status_map.get(node_id)
        badges = list(execution_badges.get(node_id, []))
        if has_blocking:
            badges.append(NodeBadgeView("validation_blocked", ui_text("graph.badge.blocked", app_language=app_language, fallback_text="Blocked"), severity="error", count=sum(1 for f in node_findings if f.blocking)))
        elif has_warning:
            badges.append(NodeBadgeView("validation_warning", ui_text("graph.badge.warning", app_language=app_language, fallback_text="Warning"), severity="warning", count=len(node_findings)))
        kind = _node_kind(node)
        if kind == "subcircuit":
            badges.append(NodeBadgeView("subgraph", ui_text("graph.badge.subcircuit", app_language=app_language, fallback_text="Subcircuit"), severity="info"))
        if kind in {"provider", "ai"}:
            badges.append(NodeBadgeView("provider", ui_text("graph.badge.provider", app_language=app_language, fallback_text="Provider"), severity="info"))
        if kind == "plugin":
            badges.append(NodeBadgeView("plugin", ui_text("graph.badge.plugin", app_language=app_language, fallback_text="Plugin"), severity="info"))
        if preview_state == "added":
            badges.append(NodeBadgeView("preview_added", ui_text("graph.badge.added", app_language=app_language, fallback_text="Added"), severity="info"))
        elif preview_state == "updated":
            badges.append(NodeBadgeView("preview_updated", ui_text("graph.badge.updated", app_language=app_language, fallback_text="Updated"), severity="info"))
        elif preview_state == "removed":
            badges.append(NodeBadgeView("preview_removed", ui_text("graph.badge.removed", app_language=app_language, fallback_text="Removed"), severity="warning"))

        status = _project_visual_status(
            preview_state=preview_state,
            has_blocking=has_blocking,
            execution_state=execution_state,
            has_warning=has_warning,
        )
        validation_state: str | None
        if has_blocking:
            validation_state = "blocked"
        elif has_warning:
            validation_state = "warning"
        elif validation_report is None:
            validation_state = None
        else:
            validation_state = "pass"

        nodes.append(
            GraphNodeView(
                node_id=node_id,
                label=_node_label(node, node_id=node_id),
                kind=kind,
                subtype=_resource_subtype(node),
                position=_node_position(node),
                size=_node_size(node),
                status=status,
                execution_state=execution_state,
                validation_state=validation_state,
                badges=badges,
                input_summary=_input_output_summary(node, key="inputs", app_language=app_language),
                output_summary=_input_output_summary(node, key="outputs", app_language=app_language),
                preview_change_state=preview_state,
                has_designer_proposal=preview_overlay is not None,
                has_blocking_findings=has_blocking,
                has_warning_findings=has_warning,
                has_execution_events=execution_state is not None,
                child_refs=_child_refs(node),
                metadata_summary=_build_node_metadata_summary(node),
            )
        )

    edges: list[GraphEdgeView] = []
    for index, edge in enumerate(source.circuit.edges):
        if not isinstance(edge, Mapping):
            continue
        from_node = _edge_endpoint(edge, "from", "from_node_id", "source") or "unknown"
        to_node = _edge_endpoint(edge, "to", "to_node_id", "target") or "unknown"
        edge_id = _derive_edge_id(edge, index, from_node=from_node, to_node=to_node)
        preview_state = "unchanged"
        status = "normal"
        if preview_overlay is not None:
            if edge_id in preview_overlay.removed_edge_ids:
                preview_state = "removed"
                status = "preview_removed"
            elif edge_id in preview_overlay.added_edge_ids:
                preview_state = "added"
                status = "preview_added"
            elif edge_id in preview_overlay.affected_edge_ids:
                preview_state = "affected"
                status = "affected"
        edges.append(
            GraphEdgeView(
                edge_id=edge_id,
                from_node_id=from_node,
                to_node_id=to_node,
                label=str(edge.get("label")) if edge.get("label") is not None else None,
                status=status,
                edge_type=str(edge.get("type")) if edge.get("type") is not None else None,
                preview_change_state=preview_state,
                metadata_summary={k: v for k, v in edge.items() if k not in {"id", "edge_id", "from", "from_node_id", "to", "to_node_id", "label", "type", "source", "target"}} or None,
            )
        )

    graph_metrics = GraphMetricsView(
        node_count=len(nodes),
        edge_count=len(edges),
        group_count=0,
        warning_count=sum(1 for node in nodes if node.status == "warning"),
        blocking_count=sum(1 for node in nodes if node.status == "blocked"),
        running_node_count=sum(1 for node in nodes if node.execution_state == "running"),
        completed_node_count=sum(1 for node in nodes if node.execution_state in {"completed", "success"}),
        failed_node_count=sum(1 for node in nodes if node.execution_state == "failed"),
        preview_added_count=len(preview_overlay.added_node_ids) if preview_overlay is not None else 0,
        preview_updated_count=len(preview_overlay.updated_node_ids) if preview_overlay is not None else 0,
        preview_removed_count=len(preview_overlay.removed_node_ids) if preview_overlay is not None else 0,
    )
    graph_findings_summary = GraphFindingsSummary(
        validation_warning_count=validation_summary.validation_warning_count,
        validation_blocking_count=validation_summary.validation_blocking_count,
        confirmation_required_count=validation_summary.confirmation_required_count,
        execution_warning_count=execution_summary.execution_warning_count,
        execution_error_count=execution_summary.execution_error_count,
        designer_pending_count=1 if isinstance(source, WorkingSaveModel) and source.designer is not None else 0,
    )

    if layout_hints is None and isinstance(source, WorkingSaveModel):
        layout = source.ui.layout or {}
        if layout:
            layout_hints = GraphLayoutHints(
                layout_mode=str(layout.get("layout_mode")) if layout.get("layout_mode") is not None else None,
                suggested_focus_node_id=str(layout.get("suggested_focus_node_id")) if layout.get("suggested_focus_node_id") is not None else None,
                suggested_zoom_region=layout.get("suggested_zoom_region") if isinstance(layout.get("suggested_zoom_region"), Mapping) else None,
                minimap_enabled=bool(layout.get("minimap_enabled")) if "minimap_enabled" in layout else None,
            )
    elif layout_hints is None and execution_record is not None:
        focus_node = _preferred_execution_focus_node(execution_record)
        if focus_node is not None:
            layout_hints = GraphLayoutHints(suggested_focus_node_id=focus_node)

    if execution_record is not None:
        graph_id = f"execution_record:{execution_record.meta.run_id}"
        graph_title = execution_record.meta.title or getattr(source.meta, "name", None)
    elif isinstance(source, WorkingSaveModel):
        graph_id = f"working_save:{source.meta.working_save_id}"
        graph_title = source.meta.name
    else:
        graph_id = f"commit_snapshot:{source.meta.commit_id}"
        graph_title = source.meta.name

    return GraphWorkspaceViewModel(
        graph_id=graph_id,
        graph_title=graph_title,
        storage_role=storage_role,
        graph_status=graph_status,
        nodes=nodes,
        edges=edges,
        groups=[],
        selected_node_ids=resolved_selected_nodes,
        selected_edge_ids=resolved_selected_edges,
        graph_metrics=graph_metrics,
        graph_findings_summary=graph_findings_summary,
        preview_overlay=preview_overlay,
        layout_hints=layout_hints,
        explanation=explanation,
    )


__all__ = [
    "GraphWorkspaceViewModel",
    "GraphNodeView",
    "GraphEdgeView",
    "GraphGroupView",
    "GraphMetricsView",
    "GraphFindingsSummary",
    "GraphPreviewOverlay",
    "GraphLayoutHints",
    "NodeBadgeView",
    "NodePosition",
    "NodeSize",
    "read_graph_view_model",
]
