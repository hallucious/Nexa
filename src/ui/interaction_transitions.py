from __future__ import annotations

from dataclasses import dataclass

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.command_routing import BuilderCommandRouteView, BuilderCommandRoutingViewModel
from src.ui.panel_coordination import BuilderPanelCoordinationStateView


@dataclass(frozen=True)
class BuilderInteractionTransitionViewModel:
    transition_status: str = "ready"
    transition_status_label: str | None = None
    source_role: str = "none"
    current_workspace_id: str = "visual_editor"
    current_panel_id: str = "graph"
    selected_action_id: str | None = None
    recommended_action_id: str | None = None
    target_workspace_id: str | None = None
    target_panel_id: str | None = None
    transition_kind: str = "stay"
    transition_kind_label: str | None = None
    can_transition: bool = False
    requires_confirmation: bool = False
    destructive: bool = False
    reason: str | None = None


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


def _current_workspace_id(
    workflow_hub: BuilderWorkflowHubViewModel | None,
    coordination_state: BuilderPanelCoordinationStateView | None,
) -> tuple[str, str]:
    active_panel = coordination_state.active_panel if coordination_state is not None else "graph"
    if workflow_hub is not None and workflow_hub.shell is not None:
        if workflow_hub.shell.shell_mode == "runtime_monitoring":
            return "runtime_monitoring", workflow_hub.shell.coordination.active_panel
        if workflow_hub.shell.shell_mode == "designer_review":
            return "node_configuration", workflow_hub.shell.coordination.active_panel
        active_panel = workflow_hub.shell.coordination.active_panel
    if active_panel in {"designer", "inspector", "validation"}:
        return "node_configuration", active_panel
    if active_panel in {"execution", "trace_timeline", "artifact"}:
        return "runtime_monitoring", active_panel
    return "visual_editor", active_panel


def _find_route(routes: list[BuilderCommandRouteView], action_id: str | None) -> BuilderCommandRouteView | None:
    if action_id is None:
        return None
    for route in routes:
        if route.action_id == action_id:
            return route
    return None


def _recommended_action_id(
    routes: list[BuilderCommandRouteView],
    workflow_hub: BuilderWorkflowHubViewModel | None,
) -> str | None:
    def first_enabled(ids: list[str]) -> str | None:
        for action_id in ids:
            route = _find_route(routes, action_id)
            if route is not None and route.enabled:
                return action_id
        return None

    source_role = workflow_hub.storage_role if workflow_hub is not None else "none"

    if workflow_hub is not None and workflow_hub.recommended_workflow_id == "execution_launch":
        if source_role == "commit_snapshot":
            return first_enabled([
                "cancel_run",
                "run_from_commit",
                "open_latest_commit",
                "select_rollback_target",
                "open_trace",
                "open_artifacts",
                "compare_runs",
                "open_diff",
            ]) or first_enabled([route.action_id for route in routes])
        if source_role == "execution_record":
            return first_enabled([
                "cancel_run",
                "open_latest_run",
                "open_trace",
                "open_artifacts",
                "compare_runs",
                "replay_latest",
                "open_diff",
            ]) or first_enabled([route.action_id for route in routes])
        return first_enabled([
            "cancel_run",
            "run_current",
            "replay_latest",
            "open_diff",
            "open_trace",
            "open_artifacts",
        ]) or first_enabled([route.action_id for route in routes])
    return first_enabled([
        "approve_for_commit",
        "commit_snapshot",
        "review_draft",
        "request_revision",
        "open_diff",
        "run_current",
        "replay_latest",
        "run_from_commit",
        "open_latest_run",
    ]) or first_enabled([route.action_id for route in routes])


def read_builder_interaction_transition_view_model(
    source: SourceLike,
    *,
    command_routing: BuilderCommandRoutingViewModel,
    workflow_hub: BuilderWorkflowHubViewModel | None = None,
    coordination_state: BuilderPanelCoordinationStateView | None = None,
    selected_action_id: str | None = None,
    explanation: str | None = None,
) -> BuilderInteractionTransitionViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    current_workspace_id, current_panel_id = _current_workspace_id(workflow_hub, coordination_state)

    recommended_action_id = _recommended_action_id(command_routing.routes, workflow_hub)
    selected_action_id = selected_action_id or recommended_action_id
    route = _find_route(command_routing.routes, selected_action_id)

    if route is None:
        return BuilderInteractionTransitionViewModel(
            transition_status="empty",
            transition_status_label=ui_text("hub.status.empty", app_language=app_language, fallback_text="empty"),
            source_role=source_role,
            current_workspace_id=current_workspace_id,
            current_panel_id=current_panel_id,
            selected_action_id=selected_action_id,
            recommended_action_id=recommended_action_id,
            reason=explanation,
        )

    if not route.enabled:
        return BuilderInteractionTransitionViewModel(
            transition_status="blocked",
            transition_status_label=ui_text("hub.status.blocked", app_language=app_language, fallback_text="blocked"),
            source_role=source_role,
            current_workspace_id=current_workspace_id,
            current_panel_id=current_panel_id,
            selected_action_id=route.action_id,
            recommended_action_id=recommended_action_id,
            target_workspace_id=route.preferred_workspace_id,
            target_panel_id=route.preferred_panel_id,
            transition_kind="blocked",
            transition_kind_label=ui_text("transition.kind.blocked", app_language=app_language, fallback_text="blocked"),
            can_transition=False,
            requires_confirmation=route.requires_confirmation,
            destructive=route.destructive,
            reason=route.reason_disabled or explanation,
        )

    if route.preferred_workspace_id != current_workspace_id:
        transition_kind = "switch_workspace"
    elif route.preferred_panel_id != current_panel_id:
        transition_kind = "focus_panel"
    else:
        transition_kind = "stay"

    return BuilderInteractionTransitionViewModel(
        transition_status="ready",
        transition_status_label=ui_text("hub.status.ready", app_language=app_language, fallback_text="ready"),
        source_role=source_role,
        current_workspace_id=current_workspace_id,
        current_panel_id=current_panel_id,
        selected_action_id=route.action_id,
        recommended_action_id=recommended_action_id,
        target_workspace_id=route.preferred_workspace_id,
        target_panel_id=route.preferred_panel_id,
        transition_kind=transition_kind,
        transition_kind_label=ui_text(f"transition.kind.{transition_kind}", app_language=app_language, fallback_text=transition_kind.replace("_", " ")),
        can_transition=True,
        requires_confirmation=route.requires_confirmation,
        destructive=route.destructive,
        reason=explanation,
    )


__all__ = [
    "BuilderInteractionTransitionViewModel",
    "read_builder_interaction_transition_view_model",
]
