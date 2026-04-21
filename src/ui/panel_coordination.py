from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.designer_panel import DesignerPanelViewModel
from src.ui.diff_viewer import DiffViewerViewModel
from src.ui.execution_panel import ExecutionPanelViewModel
from src.ui.graph_workspace import GraphWorkspaceViewModel
from src.ui.storage_panel import StoragePanelViewModel
from src.ui.validation_panel import ValidationPanelViewModel
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel
from src.ui.artifact_viewer import ArtifactViewerViewModel
from src.ui.i18n import ui_language_from_sources, ui_text

_ADVANCED_ONLY_PANELS = {"trace_timeline", "artifact", "diff"}


@dataclass(frozen=True)
class PanelBadgeView:
    panel_id: str
    badge_style: str
    count: int = 0
    label: str | None = None


@dataclass(frozen=True)
class SelectionSummaryView:
    primary_ref: str | None = None
    selected_node_ids: list[str] = field(default_factory=list)
    selected_edge_ids: list[str] = field(default_factory=list)
    selected_artifact_ids: list[str] = field(default_factory=list)
    selected_trace_event_ids: list[str] = field(default_factory=list)
    selected_storage_ref: str | None = None
    selected_diff_change_id: str | None = None


@dataclass(frozen=True)
class BuilderPanelCoordinationStateView:
    coordination_status: str = "ready"
    storage_role: str = "none"
    active_panel: str = "graph"
    visible_panels: list[str] = field(default_factory=list)
    pinned_panels: list[str] = field(default_factory=list)
    panel_order: list[str] = field(default_factory=list)
    focus_mode: str = "default"
    selection: SelectionSummaryView = field(default_factory=SelectionSummaryView)
    panel_badges: list[PanelBadgeView] = field(default_factory=list)
    stale_reference_count: int = 0
    explanation: str | None = None



def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source) -> str:
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _ui_metadata(source) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}


def _is_empty_working_save(source: WorkingSaveModel | None, *, graph_view: GraphWorkspaceViewModel | None = None) -> bool:
    if not isinstance(source, WorkingSaveModel):
        return False
    if graph_view is not None and graph_view.graph_metrics.node_count:
        return False
    if source.circuit.nodes:
        return False
    if source.circuit.edges:
        return False
    return True


def _beginner_first_success_achieved(metadata: dict[str, Any], *, execution_view: ExecutionPanelViewModel | None = None) -> bool:
    if bool(metadata.get("beginner_first_success_achieved")):
        return True
    if execution_view is not None and execution_view.execution_status == "completed" and execution_view.run_identity.run_id is not None:
        return True
    return False


def _advanced_surfaces_unlocked(metadata: dict[str, Any], *, execution_view: ExecutionPanelViewModel | None = None) -> bool:
    if bool(metadata.get("advanced_mode_requested")):
        return True
    if str(metadata.get("user_mode") or "").lower() == "advanced":
        return True
    return _beginner_first_success_achieved(metadata, execution_view=execution_view)


def _beginner_shell_active(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None,
    *,
    graph_view: GraphWorkspaceViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
) -> bool:
    if not isinstance(source, WorkingSaveModel):
        return False
    metadata = _ui_metadata(source)
    if _advanced_surfaces_unlocked(metadata, execution_view=execution_view):
        return False
    return _is_empty_working_save(source, graph_view=graph_view)


def _default_visible_panels(
    *,
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None = None,
    graph_view: GraphWorkspaceViewModel | None = None,
    storage_view: StoragePanelViewModel | None = None,
    diff_view: DiffViewerViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
    validation_view: ValidationPanelViewModel | None = None,
    designer_view: DesignerPanelViewModel | None = None,
    trace_view: TraceTimelineViewerViewModel | None = None,
    artifact_view: ArtifactViewerViewModel | None = None,
) -> list[str]:
    beginner_shell_active = _beginner_shell_active(source, graph_view=graph_view, execution_view=execution_view)
    panels: list[str] = []
    if beginner_shell_active:
        if designer_view is not None:
            panels.append("designer")
        if validation_view is not None and validation_view.overall_status == "blocked":
            panels.append("validation")
    else:
        if graph_view is not None:
            panels.extend(["graph", "inspector"])
        if validation_view is not None:
            panels.append("validation")
        if storage_view is not None:
            panels.append("storage")
        if execution_view is not None:
            panels.append("execution")
        if trace_view is not None and trace_view.timeline_status != "idle":
            panels.append("trace_timeline")
        if artifact_view is not None and artifact_view.viewer_status != "idle":
            panels.append("artifact")
        if diff_view is not None and diff_view.viewer_status != "hidden":
            panels.append("diff")
        if designer_view is not None:
            panels.append("designer")
    if not panels:
        panels.append("graph")
    seen: set[str] = set()
    ordered: list[str] = []
    for panel_id in panels:
        if panel_id not in seen:
            seen.add(panel_id)
            ordered.append(panel_id)
    return ordered

def _resolve_primary_ref(selection: SelectionSummaryView) -> str | None:
    if selection.selected_node_ids:
        return f"node:{selection.selected_node_ids[0]}"
    if selection.selected_edge_ids:
        return f"edge:{selection.selected_edge_ids[0]}"
    if selection.selected_artifact_ids:
        return f"artifact:{selection.selected_artifact_ids[0]}"
    if selection.selected_trace_event_ids:
        return f"trace_event:{selection.selected_trace_event_ids[0]}"
    if selection.selected_storage_ref:
        return selection.selected_storage_ref
    if selection.selected_diff_change_id:
        return f"diff_change:{selection.selected_diff_change_id}"
    return None


def read_panel_coordination_state(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    graph_view: GraphWorkspaceViewModel | None = None,
    storage_view: StoragePanelViewModel | None = None,
    diff_view: DiffViewerViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
    validation_view: ValidationPanelViewModel | None = None,
    designer_view: DesignerPanelViewModel | None = None,
    trace_view: TraceTimelineViewerViewModel | None = None,
    artifact_view: ArtifactViewerViewModel | None = None,
    explanation: str | None = None,
) -> BuilderPanelCoordinationStateView:
    source = _unwrap(source)
    role = _storage_role(source)
    metadata = _ui_metadata(source)
    app_language = ui_language_from_sources(source)

    selection = SelectionSummaryView(
        selected_node_ids=[str(v) for v in metadata.get("selected_node_ids", []) if v is not None],
        selected_edge_ids=[str(v) for v in metadata.get("selected_edge_ids", []) if v is not None],
        selected_artifact_ids=[str(v) for v in metadata.get("selected_artifact_ids", []) if v is not None],
        selected_trace_event_ids=[str(v) for v in metadata.get("selected_trace_event_ids", []) if v is not None],
        selected_storage_ref=str(metadata.get("selected_storage_ref")) if metadata.get("selected_storage_ref") is not None else None,
        selected_diff_change_id=str(metadata.get("selected_diff_change_id")) if metadata.get("selected_diff_change_id") is not None else None,
    )
    if graph_view is not None and graph_view.selected_node_ids:
        selection = SelectionSummaryView(
            selected_node_ids=list(graph_view.selected_node_ids),
            selected_edge_ids=list(graph_view.selected_edge_ids),
            selected_artifact_ids=selection.selected_artifact_ids,
            selected_trace_event_ids=selection.selected_trace_event_ids,
            selected_storage_ref=selection.selected_storage_ref,
            selected_diff_change_id=selection.selected_diff_change_id,
        )
    selection = SelectionSummaryView(
        primary_ref=_resolve_primary_ref(selection),
        selected_node_ids=selection.selected_node_ids,
        selected_edge_ids=selection.selected_edge_ids,
        selected_artifact_ids=selection.selected_artifact_ids,
        selected_trace_event_ids=selection.selected_trace_event_ids,
        selected_storage_ref=selection.selected_storage_ref,
        selected_diff_change_id=selection.selected_diff_change_id,
    )

    visible_panels_raw = metadata.get("visible_panels")
    if visible_panels_raw is None:
        visible_panels = _default_visible_panels(
            source=source,
            graph_view=graph_view,
            storage_view=storage_view,
            diff_view=diff_view,
            execution_view=execution_view,
            validation_view=validation_view,
            designer_view=designer_view,
            trace_view=trace_view,
            artifact_view=artifact_view,
        )
    else:
        visible_panels = [str(v) for v in visible_panels_raw if v is not None]
    pinned_panels = [str(v) for v in metadata.get("pinned_panels", []) if v is not None]
    beginner_shell_active = _beginner_shell_active(source, graph_view=graph_view, execution_view=execution_view)
    advanced_unlocked = _advanced_surfaces_unlocked(metadata, execution_view=execution_view)
    if beginner_shell_active and not advanced_unlocked:
        allowed_panels = {"designer"}
        if validation_view is not None and validation_view.overall_status == "blocked":
            allowed_panels.add("validation")
        visible_panels = [panel_id for panel_id in visible_panels if panel_id not in _ADVANCED_ONLY_PANELS and panel_id in allowed_panels]
    panel_order = [str(v) for v in metadata.get("panel_order", visible_panels) if v is not None]
    if beginner_shell_active and not advanced_unlocked:
        panel_order = [panel_id for panel_id in panel_order if panel_id not in _ADVANCED_ONLY_PANELS]
        pinned_panels = [panel_id for panel_id in pinned_panels if panel_id not in _ADVANCED_ONLY_PANELS]

    active_panel = str(metadata.get("active_panel")) if metadata.get("active_panel") else ""
    if beginner_shell_active and not advanced_unlocked and active_panel in _ADVANCED_ONLY_PANELS:
        active_panel = ""
    if not active_panel:
        if selection.selected_artifact_ids:
            active_panel = "artifact"
        elif selection.selected_trace_event_ids:
            active_panel = "trace_timeline"
        elif selection.selected_diff_change_id is not None:
            active_panel = "diff"
        elif selection.selected_storage_ref is not None:
            active_panel = "storage"
        elif beginner_shell_active and designer_view is not None:
            active_panel = "designer"
        elif execution_view is not None and execution_view.execution_status in {"running", "queued"}:
            active_panel = "execution"
        elif role == "execution_record":
            active_panel = "execution"
        elif validation_view is not None and validation_view.overall_status == "blocked":
            active_panel = "validation"
        elif role == "commit_snapshot":
            active_panel = "storage"
        elif designer_view is not None and designer_view.request_state.request_status in {"submitted", "editing"}:
            active_panel = "designer"
        elif selection.primary_ref is not None and role in {"working_save", "commit_snapshot"}:
            active_panel = "inspector"
        else:
            active_panel = "graph"

    badges: list[PanelBadgeView] = []
    if validation_view is not None:
        count = len(validation_view.blocking_findings) + len(validation_view.warning_findings) + len(validation_view.confirmation_findings)
        if count:
            style = "error" if validation_view.overall_status == "blocked" else "warning"
            badges.append(PanelBadgeView(panel_id="validation", badge_style=style, count=count, label=validation_view.overall_status))
    if execution_view is not None and execution_view.execution_status in {"running", "queued"}:
        badges.append(PanelBadgeView(panel_id="execution", badge_style="active", count=len(execution_view.recent_events), label=execution_view.execution_status))
    if designer_view is not None:
        count = designer_view.approval_state.unanswered_decision_count
        if count or designer_view.request_state.request_status in {"editing", "submitted"}:
            badges.append(PanelBadgeView(panel_id="designer", badge_style="attention", count=count, label=designer_view.request_state.request_status))
    if diff_view is not None and diff_view.viewer_status in {"ready", "partial"}:
        diff_count = sum(group.count for group in diff_view.grouped_changes)
        if diff_count:
            badges.append(PanelBadgeView(panel_id="diff", badge_style="info", count=diff_count, label=diff_view.diff_mode))
    if trace_view is not None and trace_view.timeline_status != "idle":
        event_count = len(trace_view.events)
        if event_count:
            badges.append(PanelBadgeView(panel_id="trace_timeline", badge_style="info", count=event_count, label=trace_view.timeline_status))
    if artifact_view is not None and artifact_view.viewer_status in {"ready", "partial"}:
        artifact_count = len(artifact_view.artifact_list)
        if artifact_count:
            badges.append(PanelBadgeView(panel_id="artifact", badge_style="info", count=artifact_count, label=artifact_view.viewer_status))
    if storage_view is not None and storage_view.diagnostics.lifecycle_warning_count:
        badges.append(PanelBadgeView(panel_id="storage", badge_style="warning", count=storage_view.diagnostics.lifecycle_warning_count, label=ui_text("panel.badge.storage_diagnostics", app_language=app_language, fallback_text="storage diagnostics")))

    stale_reference_count = 0
    if selection.primary_ref is None and any([
        selection.selected_node_ids,
        selection.selected_edge_ids,
        selection.selected_artifact_ids,
        selection.selected_trace_event_ids,
        selection.selected_storage_ref,
        selection.selected_diff_change_id,
    ]):
        stale_reference_count += 1
    if active_panel not in visible_panels:
        stale_reference_count += 1

    return BuilderPanelCoordinationStateView(
        storage_role=role,
        active_panel=active_panel,
        visible_panels=visible_panels,
        pinned_panels=pinned_panels,
        panel_order=panel_order,
        focus_mode=str(metadata.get("workspace_focus_mode") or ("designer" if active_panel == "designer" else "default")),
        selection=selection,
        panel_badges=badges,
        stale_reference_count=stale_reference_count,
        explanation=explanation,
    )


__all__ = [
    "PanelBadgeView",
    "SelectionSummaryView",
    "BuilderPanelCoordinationStateView",
    "read_panel_coordination_state",
]
