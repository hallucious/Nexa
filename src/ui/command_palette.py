from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.nex_contract import ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel, read_trace_timeline_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class CommandPaletteEntryView:
    entry_id: str
    entry_type: str
    label: str
    target_ref: str | None = None
    preferred_workspace_id: str = "visual_editor"
    preferred_panel_id: str = "graph"
    action_id: str | None = None
    enabled: bool = True
    reason_disabled: str | None = None


@dataclass(frozen=True)
class CommandPaletteViewModel:
    palette_status: str = "ready"
    source_role: str = "none"
    placeholder: str | None = None
    entries: list[CommandPaletteEntryView] = field(default_factory=list)
    enabled_entry_count: int = 0
    jump_entry_count: int = 0
    action_entry_count: int = 0
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None


def _unwrap(source: SourceLike):
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


def _node_entries(graph_view: GraphWorkspaceViewModel | None) -> list[CommandPaletteEntryView]:
    if graph_view is None:
        return []
    return [
        CommandPaletteEntryView(
            entry_id=f"jump:node:{node.node_id}",
            entry_type="jump",
            label=node.label,
            target_ref=f"node:{node.node_id}",
            preferred_workspace_id="visual_editor",
            preferred_panel_id="graph",
            enabled=True,
        )
        for node in graph_view.nodes
    ]


def _finding_entries(validation_view: ValidationPanelViewModel | None, *, app_language: str) -> list[CommandPaletteEntryView]:
    if validation_view is None:
        return []
    entries: list[CommandPaletteEntryView] = []
    for finding in validation_view.blocking_findings[:3] + validation_view.warning_findings[:3]:
        title = finding.title or ui_text("palette.finding.untitled", app_language=app_language, fallback_text="Validation finding")
        entries.append(
            CommandPaletteEntryView(
                entry_id=f"jump:finding:{finding.finding_id}",
                entry_type="jump",
                label=title,
                target_ref=finding.location_ref or (f"{finding.target_type}:{finding.target_id}" if finding.target_type is not None else None),
                preferred_workspace_id="node_configuration",
                preferred_panel_id="validation",
                enabled=True,
            )
        )
    return entries


def _storage_entries(storage_view: StoragePanelViewModel | None, *, app_language: str) -> list[CommandPaletteEntryView]:
    if storage_view is None:
        return []
    entries: list[CommandPaletteEntryView] = []
    if storage_view.working_save_card is not None and storage_view.working_save_card.working_save_id is not None:
        entries.append(
            CommandPaletteEntryView(
                entry_id="jump:storage:working_save",
                entry_type="jump",
                label=ui_text("palette.jump.working_save", app_language=app_language, fallback_text="Open current working save"),
                target_ref=f"working_save:{storage_view.working_save_card.working_save_id}",
                preferred_workspace_id="visual_editor",
                preferred_panel_id="storage",
            )
        )
    if storage_view.commit_snapshot_card is not None and storage_view.commit_snapshot_card.commit_id is not None:
        entries.append(
            CommandPaletteEntryView(
                entry_id="jump:storage:commit_snapshot",
                entry_type="jump",
                label=ui_text("palette.jump.commit_snapshot", app_language=app_language, fallback_text="Open latest commit snapshot"),
                target_ref=f"commit_snapshot:{storage_view.commit_snapshot_card.commit_id}",
                preferred_workspace_id="visual_editor",
                preferred_panel_id="storage",
            )
        )
    if storage_view.execution_record_card is not None and storage_view.execution_record_card.run_id is not None:
        entries.append(
            CommandPaletteEntryView(
                entry_id="jump:storage:execution_record",
                entry_type="jump",
                label=ui_text("palette.jump.execution_record", app_language=app_language, fallback_text="Open latest execution record"),
                target_ref=f"execution_record:{storage_view.execution_record_card.run_id}",
                preferred_workspace_id="runtime_monitoring",
                preferred_panel_id="execution",
            )
        )
    return entries


def _execution_entries(execution_view: ExecutionPanelViewModel | None, *, app_language: str) -> list[CommandPaletteEntryView]:
    if execution_view is None or execution_view.run_identity.run_id is None:
        return []
    return [
        CommandPaletteEntryView(
            entry_id=f"jump:run:{execution_view.run_identity.run_id}",
            entry_type="jump",
            label=ui_text("palette.jump.current_run", app_language=app_language, fallback_text="Focus current run"),
            target_ref=f"run:{execution_view.run_identity.run_id}",
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="execution",
        )
    ]


def _trace_entries(trace_view: TraceTimelineViewerViewModel | None, *, app_language: str) -> list[CommandPaletteEntryView]:
    if trace_view is None:
        return []
    run_id = trace_view.run_identity.run_id
    if run_id is None and not trace_view.events:
        return []
    return [
        CommandPaletteEntryView(
            entry_id=f"jump:trace:{run_id or 'latest'}",
            entry_type="jump",
            label=ui_text("palette.jump.trace_timeline", app_language=app_language, fallback_text="Open current trace timeline"),
            target_ref=f"trace:{run_id or 'latest'}",
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="trace_timeline",
        )
    ]


def _artifact_entries(artifact_view: ArtifactViewerViewModel | None, *, app_language: str) -> list[CommandPaletteEntryView]:
    if artifact_view is None or not artifact_view.artifact_list:
        return []
    selected = artifact_view.selected_artifact.artifact_id if artifact_view.selected_artifact is not None else artifact_view.artifact_list[0].artifact_id
    return [
        CommandPaletteEntryView(
            entry_id=f"jump:artifact:{selected}",
            entry_type="jump",
            label=ui_text("palette.jump.artifact", app_language=app_language, fallback_text="Open selected artifact"),
            target_ref=f"artifact:{selected}",
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="artifact",
        )
    ]


def _diff_entries(
    diff_view: DiffViewerViewModel | None,
    *,
    preview_overlay: GraphPreviewOverlay | None,
    app_language: str,
) -> list[CommandPaletteEntryView]:
    entries: list[CommandPaletteEntryView] = []
    if diff_view is not None and diff_view.viewer_status in {"ready", "partial"}:
        entries.append(
            CommandPaletteEntryView(
                entry_id=f"jump:diff:{diff_view.diff_mode}",
                entry_type="jump",
                label=ui_text("palette.jump.diff", app_language=app_language, fallback_text="Open current diff view"),
                target_ref=f"diff:{diff_view.diff_mode}",
                preferred_workspace_id="visual_editor",
                preferred_panel_id="diff",
            )
        )
    elif preview_overlay is not None:
        entries.append(
            CommandPaletteEntryView(
                entry_id=f"jump:preview:{preview_overlay.overlay_id}",
                entry_type="jump",
                label=ui_text("palette.jump.preview", app_language=app_language, fallback_text="Open current preview overlay"),
                target_ref=preview_overlay.preview_ref or preview_overlay.overlay_id,
                preferred_workspace_id="visual_editor",
                preferred_panel_id="diff",
            )
        )
    return entries


def _action_entries(action_schema: BuilderActionSchemaView) -> list[CommandPaletteEntryView]:
    workspace_map = {
        "run_current": ("runtime_monitoring", "execution"),
        "run_from_commit": ("runtime_monitoring", "execution"),
        "cancel_run": ("runtime_monitoring", "execution"),
        "replay_latest": ("runtime_monitoring", "trace_timeline"),
        "open_latest_run": ("runtime_monitoring", "execution"),
        "open_trace": ("runtime_monitoring", "trace_timeline"),
        "open_artifacts": ("runtime_monitoring", "artifact"),
        "approve_for_commit": ("node_configuration", "designer"),
        "request_revision": ("node_configuration", "designer"),
        "review_draft": ("node_configuration", "validation"),
        "commit_snapshot": ("node_configuration", "designer"),
        "open_latest_commit": ("visual_editor", "storage"),
        "select_rollback_target": ("visual_editor", "storage"),
        "open_diff": ("visual_editor", "diff"),
        "compare_runs": ("visual_editor", "diff"),
    }
    entries: list[CommandPaletteEntryView] = []
    for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]:
        workspace_id, panel_id = workspace_map.get(action.action_id, ("visual_editor", "graph"))
        entries.append(
            CommandPaletteEntryView(
                entry_id=f"action:{action.action_id}",
                entry_type="action",
                label=action.label,
                target_ref=None,
                preferred_workspace_id=workspace_id,
                preferred_panel_id=panel_id,
                action_id=action.action_id,
                enabled=action.enabled,
                reason_disabled=action.reason_disabled,
            )
        )
    return entries


def read_command_palette_view_model(
    source: SourceLike,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    storage_view: StoragePanelViewModel | None = None,
    validation_view: ValidationPanelViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
    trace_view: TraceTimelineViewerViewModel | None = None,
    artifact_view: ArtifactViewerViewModel | None = None,
    diff_view: DiffViewerViewModel | None = None,
    graph_view: GraphWorkspaceViewModel | None = None,
    action_schema: BuilderActionSchemaView | None = None,
    coordination_state: BuilderPanelCoordinationStateView | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> CommandPaletteViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)
    storage_view = storage_view or (read_storage_view_model(source_unwrapped) if source_unwrapped is not None else None)
    validation_view = validation_view or (read_validation_panel_view_model(source_unwrapped, validation_report=validation_report, execution_record=execution_record) if source_unwrapped is not None else None)
    execution_view = execution_view or (read_execution_panel_view_model(source_unwrapped, execution_record=execution_record) if source_unwrapped is not None else None)
    trace_view = trace_view or (read_trace_timeline_view_model(source_unwrapped if source_unwrapped is not None else execution_record, execution_record=execution_record) if (source_unwrapped is not None or execution_record is not None) else None)
    artifact_view = artifact_view or (read_artifact_viewer_view_model(source_unwrapped if source_unwrapped is not None else execution_record, execution_record=execution_record) if (source_unwrapped is not None or execution_record is not None) else None)
    graph_view = graph_view or (
        read_graph_view_model(source_unwrapped, validation_report=validation_report, execution_record=execution_record, preview_overlay=preview_overlay)
        if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel, LoadedNexArtifact))
        else None
    )
    if diff_view is None and preview_overlay is not None and source_unwrapped is not None:
        diff_view = read_diff_view_model(diff_mode="preview_vs_current", source=preview_overlay, target=source_unwrapped)
    coordination_state = coordination_state or read_panel_coordination_state(source_unwrapped, graph_view=graph_view, storage_view=storage_view, execution_view=execution_view, validation_view=validation_view)
    action_schema = action_schema or read_builder_action_schema(source_unwrapped, storage_view=storage_view, validation_view=validation_view, execution_view=execution_view)

    entries = [
        *_action_entries(action_schema),
        *_node_entries(graph_view),
        *_finding_entries(validation_view, app_language=app_language),
        *_storage_entries(storage_view, app_language=app_language),
        *_execution_entries(execution_view, app_language=app_language),
        *_trace_entries(trace_view, app_language=app_language),
        *_artifact_entries(artifact_view, app_language=app_language),
        *_diff_entries(diff_view, preview_overlay=preview_overlay, app_language=app_language),
    ]

    if approval_flow is not None and approval_flow.current_stage not in {None, "idle", "none", "completed"}:
        entries.insert(
            0,
            CommandPaletteEntryView(
                entry_id=f"jump:approval:{approval_flow.approval_id}",
                entry_type="jump",
                label=ui_text("palette.jump.approval", app_language=app_language, fallback_text="Open current approval decision"),
                target_ref=f"approval:{approval_flow.approval_id}",
                preferred_workspace_id="node_configuration",
                preferred_panel_id="designer",
            ),
        )

    enabled_entry_count = sum(1 for entry in entries if entry.enabled)
    jump_entry_count = sum(1 for entry in entries if entry.entry_type == "jump")
    action_entry_count = sum(1 for entry in entries if entry.entry_type == "action")
    palette_status = "empty" if not entries else ("attention" if any(not entry.enabled for entry in entries if entry.entry_type == "action") else "ready")

    return CommandPaletteViewModel(
        palette_status=palette_status,
        source_role=source_role,
        placeholder=ui_text("palette.placeholder", app_language=app_language, fallback_text="Search nodes, findings, runs, actions"),
        entries=entries,
        enabled_entry_count=enabled_entry_count,
        jump_entry_count=jump_entry_count,
        action_entry_count=action_entry_count,
        explanation=explanation,
    )


__all__ = ["CommandPaletteEntryView", "CommandPaletteViewModel", "read_command_palette_view_model"]
