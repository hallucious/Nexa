from __future__ import annotations

from dataclasses import dataclass, field, replace

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.designer_panel import read_designer_panel_view_model
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class EditorCanvasSummaryView:
    node_count: int = 0
    edge_count: int = 0
    selected_node_count: int = 0
    selected_edge_count: int = 0
    preview_change_count: int = 0
    blocked_finding_count: int = 0


@dataclass(frozen=True)
class EditorComparisonStateView:
    diff_mode: str | None = None
    viewer_status: str = "hidden"
    change_count: int = 0
    selected_change_id: str | None = None
    can_open_diff: bool = False


@dataclass(frozen=True)
class EditorReadinessView:
    posture: str = "unknown"
    posture_label: str | None = None
    graph_ready: bool = False
    validation_status: str = "unknown"
    selected_object_count: int = 0
    runnable: bool = False
    review_ready: bool = False
    has_execution_context: bool = False
    has_preview_overlay: bool = False
    enabled_local_action_count: int = 0


@dataclass(frozen=True)
class EditorFocusHintView:
    hint_kind: str = "overview"
    target_ref: str | None = None
    label: str | None = None
    explanation: str | None = None
    suggested_action_id: str | None = None


@dataclass(frozen=True)
class EditorSelectionSummaryView:
    selection_mode: str = "none"
    target_ref: str | None = None
    label: str | None = None
    secondary_label: str | None = None
    status: str = "unknown"
    status_label: str | None = None
    related_blocking_count: int = 0
    related_warning_count: int = 0
    has_execution_history: bool = False
    next_action_id: str | None = None
    next_action_label: str | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class EditorActionShortcutView:
    action: BuilderActionView
    target_ref: str | None = None
    priority: str = "secondary"
    emphasis: str = "neutral"
    explanation: str | None = None


@dataclass(frozen=True)
class VisualEditorWorkspaceViewModel:
    workspace_status: str = "ready"
    workspace_status_label: str | None = None
    storage_role: str = "none"
    graph: GraphWorkspaceViewModel | None = None
    diff: DiffViewerViewModel | None = None
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    storage: StoragePanelViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    canvas_summary: EditorCanvasSummaryView = field(default_factory=EditorCanvasSummaryView)
    comparison_state: EditorComparisonStateView = field(default_factory=EditorComparisonStateView)
    readiness: EditorReadinessView = field(default_factory=EditorReadinessView)
    focus_hint: EditorFocusHintView = field(default_factory=EditorFocusHintView)
    selection_summary: EditorSelectionSummaryView = field(default_factory=EditorSelectionSummaryView)
    local_actions: list[BuilderActionView] = field(default_factory=list)
    action_shortcuts: list[EditorActionShortcutView] = field(default_factory=list)
    can_edit_graph: bool = False
    can_preview_changes: bool = False
    explanation: str | None = None
    suggested_actions: list[BuilderActionView] = field(default_factory=list)


_ACTION_META: dict[str, tuple[str, str, str]] = {
    "create_circuit_from_template": ("builder.action.create_circuit_from_template", "Choose starter workflow", "template_gallery"),
    "open_provider_setup": ("builder.action.open_provider_setup", "Connect AI model", "provider_setup"),
    "open_file_input": ("builder.action.open_file_input", "Use a file", "external_input"),
    "enter_url_input": ("builder.action.enter_url_input", "Use a URL", "external_input"),
    "open_diff": ("builder.action.open_diff", "Open diff", "comparison"),
    "open_node_configuration": ("builder.action.open_node_configuration", "Open configuration", "workspace_navigation"),
    "open_runtime_monitoring": ("builder.action.open_runtime_monitoring", "Open runtime monitoring", "workspace_navigation"),
}


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



def _workspace_explanation(
    *,
    workspace_status: str,
    app_language: str,
    validation_vm: ValidationPanelViewModel | None,
    preview_overlay: GraphPreviewOverlay | None,
) -> str | None:
    if workspace_status == "empty":
        return ui_text("workspace.visual_editor.explanation.empty", app_language=app_language)
    if workspace_status == "blocked":
        if validation_vm is not None and validation_vm.beginner_summary.cause:
            return validation_vm.beginner_summary.cause
        return ui_text("workspace.visual_editor.explanation.blocked", app_language=app_language)
    if workspace_status == "previewing":
        if preview_overlay is not None and preview_overlay.summary:
            return preview_overlay.summary
        return ui_text("workspace.visual_editor.explanation.previewing", app_language=app_language)
    if workspace_status == "reviewing":
        return ui_text("workspace.visual_editor.explanation.reviewing", app_language=app_language)
    return None



def _action_lookup(action_schema: BuilderActionSchemaView) -> dict[str, BuilderActionView]:
    return {
        action.action_id: action
        for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    }



def _scoped_action(action: BuilderActionView) -> BuilderActionView:
    return replace(action, target_scope="visual_editor")



def _manual_action(
    action_id: str,
    *,
    app_language: str,
    enabled: bool,
    reason_disabled: str | None = None,
) -> BuilderActionView:
    text_key, fallback_text, action_kind = _ACTION_META[action_id]
    return BuilderActionView(
        action_id=action_id,
        label=ui_text(text_key, app_language=app_language, fallback_text=fallback_text),
        action_kind=action_kind,
        enabled=enabled,
        reason_disabled=reason_disabled,
        target_scope="visual_editor",
    )



def _unique_actions(actions: list[BuilderActionView | None]) -> list[BuilderActionView]:
    deduped: list[BuilderActionView] = []
    seen: set[str] = set()
    for action in actions:
        if action is None or action.action_id in seen:
            continue
        seen.add(action.action_id)
        deduped.append(action)
    return deduped



def _action_or_manual(
    action_map: dict[str, BuilderActionView],
    action_id: str,
    *,
    app_language: str,
    enabled: bool = True,
    reason_disabled: str | None = None,
) -> BuilderActionView | None:
    action = action_map.get(action_id)
    if action is not None:
        return _scoped_action(action)
    if action_id in _ACTION_META:
        return _manual_action(action_id, app_language=app_language, enabled=enabled, reason_disabled=reason_disabled)
    return None



def _workspace_local_actions(
    *,
    workspace_status: str,
    storage_role: str,
    app_language: str,
    action_schema: BuilderActionSchemaView,
    graph_vm: GraphWorkspaceViewModel | None,
    comparison_state: EditorComparisonStateView,
    has_execution_context: bool,
    can_run: bool,
    review_ready: bool,
) -> list[BuilderActionView]:
    action_map = _action_lookup(action_schema)
    has_selection = bool(graph_vm is not None and (graph_vm.selected_node_ids or graph_vm.selected_edge_ids))
    graph_navigation_available = graph_vm is not None and graph_vm.graph_metrics.node_count > 0
    diff_reason = None if comparison_state.can_open_diff else ui_text("builder.reason.diff_requires_comparison_target", app_language=app_language)
    graph_reason = None if graph_navigation_available else ui_text("builder.reason.configuration_requires_graph", app_language=app_language)
    runtime_reason = None if has_execution_context else ui_text("builder.reason.runtime_monitoring_requires_execution", app_language=app_language)

    if workspace_status == "empty":
        return _unique_actions([
            _action_or_manual(action_map, "create_circuit_from_template", app_language=app_language, enabled=storage_role == "working_save"),
            _action_or_manual(action_map, "open_provider_setup", app_language=app_language, enabled=storage_role == "working_save"),
            _action_or_manual(action_map, "open_file_input", app_language=app_language, enabled=storage_role == "working_save"),
            _action_or_manual(action_map, "enter_url_input", app_language=app_language, enabled=storage_role == "working_save"),
        ])

    if workspace_status == "blocked":
        return _unique_actions([
            _action_or_manual(action_map, "open_node_configuration", app_language=app_language, enabled=graph_navigation_available, reason_disabled=graph_reason),
            _action_or_manual(action_map, "request_revision", app_language=app_language),
            _action_or_manual(action_map, "open_provider_setup", app_language=app_language, enabled=storage_role == "working_save"),
            _action_or_manual(action_map, "open_diff", app_language=app_language, enabled=comparison_state.can_open_diff, reason_disabled=diff_reason),
        ])

    if workspace_status == "previewing":
        return _unique_actions([
            _action_or_manual(action_map, "review_draft", app_language=app_language),
            _action_or_manual(action_map, "commit_snapshot", app_language=app_language),
            _action_or_manual(action_map, "open_diff", app_language=app_language, enabled=comparison_state.can_open_diff, reason_disabled=diff_reason),
            _action_or_manual(action_map, "open_node_configuration", app_language=app_language, enabled=graph_navigation_available, reason_disabled=graph_reason),
        ])

    if workspace_status == "editing":
        return _unique_actions([
            _action_or_manual(action_map, "open_node_configuration", app_language=app_language, enabled=graph_navigation_available, reason_disabled=graph_reason) if has_selection or graph_navigation_available else None,
            _action_or_manual(action_map, "run_current", app_language=app_language) if can_run else None,
            _action_or_manual(action_map, "review_draft", app_language=app_language) if review_ready else None,
            _action_or_manual(action_map, "open_runtime_monitoring", app_language=app_language, enabled=has_execution_context, reason_disabled=runtime_reason) if has_execution_context else None,
            _action_or_manual(action_map, "open_provider_setup", app_language=app_language, enabled=storage_role == "working_save"),
        ])

    if workspace_status == "reviewing":
        return _unique_actions([
            _action_or_manual(action_map, "open_runtime_monitoring", app_language=app_language, enabled=has_execution_context, reason_disabled=runtime_reason) if has_execution_context else None,
            _action_or_manual(action_map, "open_diff", app_language=app_language, enabled=comparison_state.can_open_diff, reason_disabled=diff_reason),
            _action_or_manual(action_map, "replay_latest", app_language=app_language),
            _action_or_manual(action_map, "open_result_history", app_language=app_language),
        ])

    return _unique_actions([
        _action_or_manual(action_map, "open_node_configuration", app_language=app_language, enabled=graph_navigation_available, reason_disabled=graph_reason),
        _action_or_manual(action_map, "open_diff", app_language=app_language, enabled=comparison_state.can_open_diff, reason_disabled=diff_reason),
        _action_or_manual(action_map, "open_runtime_monitoring", app_language=app_language, enabled=has_execution_context, reason_disabled=runtime_reason) if has_execution_context else None,
    ])



def _workspace_suggested_actions(
    *,
    workspace_status: str,
    local_actions: list[BuilderActionView],
) -> list[BuilderActionView]:
    if workspace_status in {"empty", "blocked", "previewing", "editing", "reviewing"}:
        return local_actions[:3]
    return local_actions[:2]



def _readiness_posture(
    *,
    workspace_status: str,
    storage_role: str,
    has_execution_context: bool,
    has_preview_overlay: bool,
) -> str:
    if workspace_status == "empty":
        return "creation"
    if workspace_status == "blocked":
        return "repair"
    if workspace_status == "previewing" or has_preview_overlay:
        return "preview_review"
    if workspace_status == "editing" and has_execution_context:
        return "run_linked_editing"
    if workspace_status == "editing":
        return "active_editing"
    if workspace_status == "reviewing" and has_execution_context:
        return "run_linked_review"
    if workspace_status == "reviewing":
        return "review_only"
    if storage_role == "execution_record":
        return "run_linked_review"
    return "view_only"



def _editor_readiness(
    *,
    workspace_status: str,
    storage_role: str,
    graph_vm: GraphWorkspaceViewModel | None,
    validation_vm: ValidationPanelViewModel | None,
    has_execution_context: bool,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> EditorReadinessView:
    selected_object_count = 0
    if graph_vm is not None:
        selected_object_count = len(graph_vm.selected_node_ids) + len(graph_vm.selected_edge_ids)
    runnable = any(action.action_id in {"run_current", "run_from_commit"} and action.enabled for action in local_actions)
    review_ready = any(action.action_id in {"review_draft", "commit_snapshot", "approve_for_commit"} and action.enabled for action in local_actions)
    posture = _readiness_posture(
        workspace_status=workspace_status,
        storage_role=storage_role,
        has_execution_context=has_execution_context,
        has_preview_overlay=bool(graph_vm is not None and graph_vm.preview_overlay is not None),
    )
    return EditorReadinessView(
        posture=posture,
        posture_label=ui_text(f"workspace.visual_editor.readiness.{posture}", app_language=app_language, fallback_text=posture.replace("_", " ")),
        graph_ready=bool(graph_vm is not None and graph_vm.graph_metrics.node_count > 0),
        validation_status=validation_vm.overall_status if validation_vm is not None else "unknown",
        selected_object_count=selected_object_count,
        runnable=runnable,
        review_ready=review_ready,
        has_execution_context=has_execution_context,
        has_preview_overlay=bool(graph_vm is not None and graph_vm.preview_overlay is not None),
        enabled_local_action_count=sum(1 for action in local_actions if action.enabled),
    )



def _editor_focus_hint(
    *,
    workspace_status: str,
    graph_vm: GraphWorkspaceViewModel | None,
    has_execution_context: bool,
    app_language: str,
) -> EditorFocusHintView:
    if graph_vm is None or (graph_vm.graph_metrics.node_count == 0 and graph_vm.graph_metrics.edge_count == 0):
        return EditorFocusHintView(
            hint_kind="empty_canvas",
            explanation=ui_text(
                "workspace.visual_editor.focus.empty",
                app_language=app_language,
                fallback_text="Use the editor actions to create your first workflow.",
            ),
            suggested_action_id="create_circuit_from_template",
        )

    node_labels = {node.node_id: node.label for node in graph_vm.nodes}

    if has_execution_context and workspace_status == "reviewing" and graph_vm.layout_hints is not None and graph_vm.layout_hints.suggested_focus_node_id is not None:
        focus_node_id = graph_vm.layout_hints.suggested_focus_node_id
        label = node_labels.get(focus_node_id, focus_node_id)
        return EditorFocusHintView(
            hint_kind="run_focus",
            target_ref=f"node:{focus_node_id}",
            label=label,
            explanation=ui_text(
                "workspace.visual_editor.focus.run_focus",
                app_language=app_language,
                fallback_text="Recent run activity points to {label}. Open runtime monitoring to inspect it.",
                label=label,
            ),
            suggested_action_id="open_runtime_monitoring",
        )

    if graph_vm.selected_node_ids:
        selected_node_id = graph_vm.selected_node_ids[0]
        count = len(graph_vm.selected_node_ids)
        label = node_labels.get(selected_node_id, selected_node_id)
        return EditorFocusHintView(
            hint_kind="node_selection",
            target_ref=f"node:{selected_node_id}",
            label=label,
            explanation=ui_text(
                "workspace.visual_editor.focus.node_selection",
                app_language=app_language,
                fallback_text="Selected {count} step(s). Open configuration to inspect details.",
                count=count,
                label=label,
            ),
            suggested_action_id="open_node_configuration",
        )

    if graph_vm.selected_edge_ids:
        selected_edge_id = graph_vm.selected_edge_ids[0]
        count = len(graph_vm.selected_edge_ids)
        return EditorFocusHintView(
            hint_kind="edge_selection",
            target_ref=f"edge:{selected_edge_id}",
            label=selected_edge_id,
            explanation=ui_text(
                "workspace.visual_editor.focus.edge_selection",
                app_language=app_language,
                fallback_text="Selected {count} connection(s). Review how this handoff is wired.",
                count=count,
            ),
            suggested_action_id="open_node_configuration",
        )

    overview_key = "workspace.visual_editor.focus.review_overview" if workspace_status == "reviewing" else "workspace.visual_editor.focus.overview"
    return EditorFocusHintView(
        hint_kind="overview",
        explanation=ui_text(
            overview_key,
            app_language=app_language,
            fallback_text=(
                "Review the graph with its comparison and recent run context."
                if workspace_status == "reviewing"
                else "Select a step or connection to inspect it in more detail."
            ),
        ),
        suggested_action_id=("open_diff" if workspace_status == "reviewing" else "open_node_configuration"),
    )




def _target_finding_counts(*, validation_report: ValidationReport | None, target_ref: str | None) -> tuple[int, int]:
    if validation_report is None or target_ref is None:
        return 0, 0
    blocking = 0
    warning = 0
    for finding in validation_report.findings:
        if finding.location != target_ref:
            continue
        if finding.blocking:
            blocking += 1
        else:
            warning += 1
    return blocking, warning


def _action_label(action: BuilderActionView | None, *, app_language: str) -> str | None:
    if action is None:
        return None
    return action.label or ui_text(
        f"builder.action.{action.action_id}",
        app_language=app_language,
        fallback_text=action.action_id.replace("_", " "),
    )


def _selection_summary_status_label(status: str, *, app_language: str) -> str:
    return ui_text(
        f"workspace.visual_editor.selection.status.{status}",
        app_language=app_language,
        fallback_text=status.replace("_", " "),
    )


def _editor_selection_summary(
    *,
    workspace_status: str,
    graph_vm: GraphWorkspaceViewModel | None,
    validation_report: ValidationReport | None,
    local_actions: list[BuilderActionView],
    has_execution_context: bool,
    app_language: str,
) -> EditorSelectionSummaryView:
    primary_action = local_actions[0] if local_actions else None
    if graph_vm is None or (graph_vm.graph_metrics.node_count == 0 and graph_vm.graph_metrics.edge_count == 0):
        return EditorSelectionSummaryView(
            selection_mode="none",
            status="empty",
            status_label=_selection_summary_status_label("empty", app_language=app_language),
            next_action_id=(primary_action.action_id if primary_action else "create_circuit_from_template"),
            next_action_label=_action_label(primary_action, app_language=app_language)
            or ui_text(
                "builder.action.create_circuit_from_template",
                app_language=app_language,
                fallback_text="Choose starter workflow",
            ),
            explanation=ui_text(
                "workspace.visual_editor.selection.none",
                app_language=app_language,
                fallback_text="Nothing is selected yet. Start by creating a workflow or choosing a starter template.",
            ),
        )

    node_map = {node.node_id: node for node in graph_vm.nodes}
    edge_map = {edge.edge_id: edge for edge in graph_vm.edges}
    run_focus_node_id = (
        graph_vm.layout_hints.suggested_focus_node_id
        if workspace_status == "reviewing" and has_execution_context and graph_vm.layout_hints is not None
        else None
    )

    if run_focus_node_id is not None and run_focus_node_id in node_map:
        node = node_map[run_focus_node_id]
        target_ref = f"node:{node.node_id}"
        blocking_count, warning_count = _target_finding_counts(
            validation_report=validation_report,
            target_ref=target_ref,
        )
        runtime_action = next((a for a in local_actions if a.action_id == "open_runtime_monitoring"), primary_action)
        return EditorSelectionSummaryView(
            selection_mode="run_focus",
            target_ref=target_ref,
            label=node.label,
            secondary_label=node.kind,
            status=node.status,
            status_label=_selection_summary_status_label(node.status, app_language=app_language),
            related_blocking_count=blocking_count,
            related_warning_count=warning_count,
            has_execution_history=(node.has_execution_events or node.execution_state is not None),
            next_action_id=(runtime_action.action_id if runtime_action else None),
            next_action_label=_action_label(runtime_action, app_language=app_language),
            explanation=ui_text(
                "workspace.visual_editor.selection.run_focus",
                app_language=app_language,
                fallback_text="Recent run activity points to {label}. Open runtime monitoring to inspect it.",
                label=node.label,
            ),
        )

    if graph_vm.selected_node_ids:
        node = node_map[graph_vm.selected_node_ids[0]]
        target_ref = f"node:{node.node_id}"
        blocking_count, warning_count = _target_finding_counts(
            validation_report=validation_report,
            target_ref=target_ref,
        )
        next_action = next((a for a in local_actions if a.action_id == "open_node_configuration"), primary_action)
        return EditorSelectionSummaryView(
            selection_mode="node",
            target_ref=target_ref,
            label=node.label,
            secondary_label=node.kind,
            status=node.status,
            status_label=_selection_summary_status_label(node.status, app_language=app_language),
            related_blocking_count=blocking_count,
            related_warning_count=warning_count,
            has_execution_history=(node.has_execution_events or node.execution_state is not None),
            next_action_id=(next_action.action_id if next_action else None),
            next_action_label=_action_label(next_action, app_language=app_language),
            explanation=ui_text(
                "workspace.visual_editor.selection.node_blocked"
                if blocking_count > 0
                else "workspace.visual_editor.selection.node",
                app_language=app_language,
                fallback_text=(
                    "The selected step has blocking issues. Open configuration and fix it first."
                    if blocking_count > 0
                    else "Selected step {label}. Open configuration to inspect its settings."
                ),
                label=node.label,
            ),
        )

    if graph_vm.selected_edge_ids:
        edge = edge_map[graph_vm.selected_edge_ids[0]]
        target_ref = f"edge:{edge.edge_id}"
        blocking_count, warning_count = _target_finding_counts(
            validation_report=validation_report,
            target_ref=target_ref,
        )
        next_action = next((a for a in local_actions if a.action_id == "open_node_configuration"), primary_action)
        return EditorSelectionSummaryView(
            selection_mode="edge",
            target_ref=target_ref,
            label=edge.label or edge.edge_id,
            secondary_label=f"{edge.from_node_id} → {edge.to_node_id}",
            status=edge.status,
            status_label=_selection_summary_status_label(edge.status, app_language=app_language),
            related_blocking_count=blocking_count,
            related_warning_count=warning_count,
            has_execution_history=False,
            next_action_id=(next_action.action_id if next_action else None),
            next_action_label=_action_label(next_action, app_language=app_language),
            explanation=ui_text(
                "workspace.visual_editor.selection.edge",
                app_language=app_language,
                fallback_text="Selected connection {label}. Review how data moves across this handoff.",
                label=edge.label or edge.edge_id,
            ),
        )

    next_action = primary_action
    overview_status = "graph_overview_review" if workspace_status == "reviewing" else "graph_overview"
    return EditorSelectionSummaryView(
        selection_mode="overview",
        status=overview_status,
        status_label=_selection_summary_status_label(overview_status, app_language=app_language),
        related_blocking_count=validation_report.blocking_count if validation_report is not None else 0,
        related_warning_count=validation_report.warning_count if validation_report is not None else 0,
        has_execution_history=has_execution_context,
        next_action_id=(next_action.action_id if next_action else None),
        next_action_label=_action_label(next_action, app_language=app_language),
        explanation=ui_text(
            "workspace.visual_editor.selection.overview",
            app_language=app_language,
            fallback_text="Graph overview: {node_count} steps, {edge_count} connections.",
            node_count=graph_vm.graph_metrics.node_count,
            edge_count=graph_vm.graph_metrics.edge_count,
        ),
    )


def _shortcut_key(action_id: str) -> str:
    mapping = {
        "create_circuit_from_template": "create",
        "open_provider_setup": "setup_provider",
        "open_file_input": "add_input",
        "open_node_configuration": "configure_selection",
        "request_revision": "request_revision",
        "open_diff": "review_diff",
        "review_draft": "review_preview",
        "commit_snapshot": "commit_preview",
        "run_current": "run_graph",
        "open_runtime_monitoring": "inspect_run_focus",
        "replay_latest": "replay_latest",
    }
    return mapping.get(action_id, action_id)


def _editor_action_shortcuts(
    *,
    workspace_status: str,
    selection_summary: EditorSelectionSummaryView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> list[EditorActionShortcutView]:
    if workspace_status == "empty":
        configs = [
            ("create_circuit_from_template", "primary", "creation"),
            ("open_provider_setup", "secondary", "setup"),
            ("open_file_input", "secondary", "input"),
        ]
    elif workspace_status == "blocked":
        configs = [
            ("open_node_configuration", "primary", "repair"),
            ("request_revision", "secondary", "review"),
            ("open_provider_setup", "secondary", "setup"),
            ("open_diff", "secondary", "comparison"),
        ]
    elif workspace_status == "previewing":
        configs = [
            ("review_draft", "primary", "review"),
            ("commit_snapshot", "secondary", "approval"),
            ("open_diff", "secondary", "comparison"),
        ]
    elif workspace_status == "reviewing":
        configs = [
            ("open_runtime_monitoring", "primary", "runtime"),
            ("open_diff", "secondary", "comparison"),
            ("replay_latest", "secondary", "runtime"),
        ]
    else:
        configs = [
            ("open_node_configuration", "primary", "selection"),
            ("review_draft", "secondary", "review"),
            ("run_current", "secondary", "run"),
        ]

    action_map = {action.action_id: action for action in local_actions}
    out: list[EditorActionShortcutView] = []
    for action_id, priority, emphasis in configs:
        action = action_map.get(action_id)
        if action is None:
            continue
        out.append(
            EditorActionShortcutView(
                action=action,
                target_ref=selection_summary.target_ref,
                priority=priority,
                emphasis=emphasis,
                explanation=ui_text(
                    f"workspace.visual_editor.shortcut.{_shortcut_key(action_id)}",
                    app_language=app_language,
                    fallback_text=action.label,
                ),
            )
        )
    return out

def read_visual_editor_workspace_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    diff_mode: str | None = None,
    diff_source=None,
    diff_target=None,
    explanation: str | None = None,
) -> VisualEditorWorkspaceViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    graph_vm = read_graph_view_model(
        source,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
    ) if source is not None else None
    storage_vm = read_storage_view_model(
        source_unwrapped,
        latest_execution_record=(execution_record if execution_record is not None and not isinstance(source_unwrapped, ExecutionRecordModel) else None),
    ) if source_unwrapped is not None else None
    validation_vm = read_validation_panel_view_model(source_unwrapped, validation_report=validation_report, execution_record=execution_record) if source_unwrapped is not None else None
    designer_vm = read_designer_panel_view_model(source_unwrapped) if source_unwrapped is not None else None
    execution_source = source_unwrapped if source_unwrapped is not None else execution_record
    execution_vm = read_execution_panel_view_model(execution_source, execution_record=execution_record) if execution_source is not None else None

    diff_vm = None
    if diff_mode and diff_source is not None and diff_target is not None:
        diff_vm = read_diff_view_model(diff_mode=diff_mode, source=diff_source, target=diff_target)
    elif preview_overlay is not None and source_unwrapped is not None:
        diff_vm = read_diff_view_model(diff_mode="preview_vs_current", source=preview_overlay, target=source_unwrapped)

    coordination_vm = read_panel_coordination_state(
        source_unwrapped,
        graph_view=graph_vm,
        storage_view=storage_vm,
        diff_view=diff_vm,
        validation_view=validation_vm,
    )
    action_schema = read_builder_action_schema(
        source_unwrapped,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        designer_view=designer_vm,
        app_language=app_language,
    )

    preview_change_count = 0
    if graph_vm is not None and graph_vm.preview_overlay is not None:
        overlay = graph_vm.preview_overlay
        preview_change_count = len(overlay.added_node_ids) + len(overlay.updated_node_ids) + len(overlay.removed_edge_ids)

    canvas_summary = EditorCanvasSummaryView(
        node_count=graph_vm.graph_metrics.node_count if graph_vm is not None else 0,
        edge_count=graph_vm.graph_metrics.edge_count if graph_vm is not None else 0,
        selected_node_count=len(graph_vm.selected_node_ids) if graph_vm is not None else 0,
        selected_edge_count=len(graph_vm.selected_edge_ids) if graph_vm is not None else 0,
        preview_change_count=preview_change_count,
        blocked_finding_count=validation_vm.summary.blocking_count if validation_vm is not None else 0,
    )
    comparison_state = EditorComparisonStateView(
        diff_mode=diff_vm.diff_mode if diff_vm is not None else None,
        viewer_status=diff_vm.viewer_status if diff_vm is not None else "hidden",
        change_count=sum(group.count for group in diff_vm.grouped_changes) if diff_vm is not None else 0,
        selected_change_id=diff_vm.selected_change.change_id if diff_vm is not None and diff_vm.selected_change is not None else None,
        can_open_diff=any(action.action_id in {"open_diff", "compare_runs"} and action.enabled for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]) or diff_vm is not None,
    )

    if graph_vm is None:
        workspace_status = "empty"
    elif storage_role == "working_save" and graph_vm.graph_metrics.node_count == 0 and graph_vm.graph_metrics.edge_count == 0:
        workspace_status = "empty"
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        workspace_status = "blocked"
    elif graph_vm.preview_overlay is not None:
        workspace_status = "previewing"
    else:
        has_review_context = storage_role != "working_save" and (
            execution_record is not None
            or (storage_vm is not None and storage_vm.execution_record_card is not None and storage_vm.execution_record_card.run_id is not None)
            or comparison_state.can_open_diff
        )
        if storage_role == "working_save":
            workspace_status = "editing"
        elif has_review_context:
            workspace_status = "reviewing"
        else:
            workspace_status = "viewing"

    workspace_explanation = explanation or _workspace_explanation(
        workspace_status=workspace_status,
        app_language=app_language,
        validation_vm=validation_vm,
        preview_overlay=(graph_vm.preview_overlay if graph_vm is not None else preview_overlay),
    )

    has_execution_context = bool(
        execution_record is not None
        or (storage_vm is not None and storage_vm.execution_record_card is not None and storage_vm.execution_record_card.run_id is not None)
    )
    action_list = [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    can_run = any(action.action_id in {"run_current", "run_from_commit"} and action.enabled for action in action_list)
    review_ready = any(action.action_id in {"review_draft", "commit_snapshot", "approve_for_commit"} and action.enabled for action in action_list)
    local_actions = _workspace_local_actions(
        workspace_status=workspace_status,
        storage_role=storage_role,
        app_language=app_language,
        action_schema=action_schema,
        graph_vm=graph_vm,
        comparison_state=comparison_state,
        has_execution_context=has_execution_context,
        can_run=can_run,
        review_ready=review_ready,
    )
    suggested_actions = _workspace_suggested_actions(
        workspace_status=workspace_status,
        local_actions=local_actions,
    )
    readiness = _editor_readiness(
        workspace_status=workspace_status,
        storage_role=storage_role,
        graph_vm=graph_vm,
        validation_vm=validation_vm,
        has_execution_context=has_execution_context,
        local_actions=local_actions,
        app_language=app_language,
    )
    focus_hint = _editor_focus_hint(
        workspace_status=workspace_status,
        graph_vm=graph_vm,
        has_execution_context=has_execution_context,
        app_language=app_language,
    )
    selection_summary = _editor_selection_summary(
        workspace_status=workspace_status,
        graph_vm=graph_vm,
        validation_report=validation_report,
        local_actions=local_actions,
        has_execution_context=has_execution_context,
        app_language=app_language,
    )
    action_shortcuts = _editor_action_shortcuts(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        local_actions=local_actions,
        app_language=app_language,
    )

    return VisualEditorWorkspaceViewModel(
        workspace_status=workspace_status,
        workspace_status_label=ui_text(f"workspace.visual_editor.status.{workspace_status}", app_language=app_language, fallback_text=workspace_status.replace("_", " ")),
        storage_role=storage_role,
        graph=graph_vm,
        diff=diff_vm,
        coordination=coordination_vm,
        action_schema=action_schema,
        storage=storage_vm,
        validation=validation_vm,
        canvas_summary=canvas_summary,
        comparison_state=comparison_state,
        readiness=readiness,
        focus_hint=focus_hint,
        selection_summary=selection_summary,
        local_actions=local_actions,
        action_shortcuts=action_shortcuts,
        can_edit_graph=storage_role == "working_save",
        can_preview_changes=graph_vm is not None and graph_vm.preview_overlay is not None,
        explanation=workspace_explanation,
        suggested_actions=suggested_actions,
    )


__all__ = [
    "EditorCanvasSummaryView",
    "EditorComparisonStateView",
    "EditorReadinessView",
    "EditorFocusHintView",
    "EditorSelectionSummaryView",
    "EditorActionShortcutView",
    "VisualEditorWorkspaceViewModel",
    "read_visual_editor_workspace_view_model",
]
