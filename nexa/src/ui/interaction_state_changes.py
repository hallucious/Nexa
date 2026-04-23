from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_dispatch_hub import BuilderDispatchHubViewModel, read_builder_dispatch_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.command_execution_adapter import CommandExecutionAdapterViewModel, read_command_execution_adapter_view_model


@dataclass(frozen=True)
class InteractionStateChangeView:
    change_id: str
    action_id: str
    current_stage_id: str
    target_stage_id: str
    current_workspace_id: str
    target_workspace_id: str
    current_panel_id: str
    target_panel_id: str
    state_change_kind: str
    action_label: str | None = None
    state_change_kind_label: str | None = None
    apply_allowed: bool = False
    optimistic_ui_allowed: bool = False
    requires_confirmation: bool = False
    side_effect_scope: str = "none"
    reason_blocked: str | None = None


@dataclass(frozen=True)
class InteractionStateChangeViewModel:
    state_change_status: str = "ready"
    state_change_status_label: str | None = None
    source_role: str = "none"
    changes: list[InteractionStateChangeView] = field(default_factory=list)
    enabled_change_count: int = 0
    blocked_change_count: int = 0
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


def _target_stage(action_id: str, current_stage_id: str) -> str:
    mapping = {
        "save_working_save": "drafting",
        "review_draft": "review",
        "approve_for_commit": "review",
        "request_revision": "drafting",
        "commit_snapshot": "commit",
        "open_latest_commit": "commit",
        "select_rollback_target": "commit",
        "run_current": "execution",
        "run_from_commit": "execution",
        "cancel_run": "execution",
        "replay_latest": "history",
        "open_latest_run": "history",
        "open_trace": "history",
        "open_artifacts": "history",
        "compare_runs": "history",
        "open_diff": current_stage_id,
    }
    return mapping.get(action_id, current_stage_id)


def _change_kind(current_workspace: str, target_workspace: str, current_panel: str, target_panel: str, stage_changed: bool) -> str:
    if stage_changed:
        return "lifecycle_transition"
    if current_workspace != target_workspace:
        return "workspace_transition"
    if current_panel != target_panel:
        return "panel_transition"
    return "in_place"


def read_interaction_state_change_view_model(
    source: SourceLike,
    *,
    dispatch_hub: BuilderDispatchHubViewModel | None = None,
    execution_adapters: CommandExecutionAdapterViewModel | None = None,
    explanation: str | None = None,
) -> InteractionStateChangeViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    dispatch_hub = dispatch_hub or read_builder_dispatch_hub_view_model(source_unwrapped)
    execution_adapters = execution_adapters or read_command_execution_adapter_view_model(source_unwrapped, dispatch_hub=dispatch_hub)

    current_stage_id = dispatch_hub.lifecycle.current_stage_id if dispatch_hub.lifecycle is not None else "drafting"
    current_workspace_id = dispatch_hub.interaction_hub.active_workspace_id if dispatch_hub.interaction_hub is not None else "visual_editor"
    current_panel_id = dispatch_hub.interaction_hub.interaction_transition.current_panel_id if dispatch_hub.interaction_hub is not None else "graph"
    routes_by_action = {route.action_id: route for route in dispatch_hub.interaction_hub.command_routing.routes} if dispatch_hub.interaction_hub is not None and dispatch_hub.interaction_hub.command_routing is not None else {}

    changes: list[InteractionStateChangeView] = []
    for adapter in execution_adapters.adapters:
        route = routes_by_action.get(adapter.action_id)
        if route is None:
            continue
        target_stage_id = _target_stage(adapter.action_id, current_stage_id)
        state_change_kind = _change_kind(
            current_workspace_id,
            route.preferred_workspace_id,
            current_panel_id,
            route.preferred_panel_id,
            target_stage_id != current_stage_id,
        )
        optimistic_ui_allowed = adapter.execute_allowed and adapter.dispatch_mode in {"synchronous", "navigation"}
        changes.append(
            InteractionStateChangeView(
                change_id=f"change:{adapter.action_id}",
                action_id=adapter.action_id,
                action_label=route.label,
                current_stage_id=current_stage_id,
                target_stage_id=target_stage_id,
                current_workspace_id=current_workspace_id,
                target_workspace_id=route.preferred_workspace_id,
                current_panel_id=current_panel_id,
                target_panel_id=route.preferred_panel_id,
                state_change_kind=state_change_kind,
                state_change_kind_label=ui_text(f"transition.kind.{state_change_kind}", app_language=app_language, fallback_text=state_change_kind.replace("_", " ")),
                apply_allowed=adapter.execute_allowed,
                optimistic_ui_allowed=optimistic_ui_allowed,
                requires_confirmation=route.requires_confirmation,
                side_effect_scope=adapter.side_effect_scope,
                reason_blocked=adapter.reason_blocked if not adapter.execute_allowed else None,
            )
        )

    enabled_change_count = sum(1 for item in changes if item.apply_allowed)
    blocked_change_count = len(changes) - enabled_change_count
    if not changes:
        state_change_status = "empty"
    elif blocked_change_count == len(changes):
        state_change_status = "blocked"
    elif blocked_change_count:
        state_change_status = "attention"
    else:
        state_change_status = "ready"

    return InteractionStateChangeViewModel(
        state_change_status=state_change_status,
        state_change_status_label=ui_text(f"hub.status.{state_change_status}", app_language=app_language, fallback_text=state_change_status.replace("_", " ")),
        source_role=source_role,
        changes=changes,
        enabled_change_count=enabled_change_count,
        blocked_change_count=blocked_change_count,
        explanation=explanation,
    )


__all__ = [
    "InteractionStateChangeView",
    "InteractionStateChangeViewModel",
    "read_interaction_state_change_view_model",
]
