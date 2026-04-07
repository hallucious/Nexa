from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_execution_adapter_hub import BuilderExecutionAdapterHubViewModel, read_builder_execution_adapter_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class EndUserCommandFlowStepView:
    step_id: str
    label: str
    status: str
    boundary: str


@dataclass(frozen=True)
class EndUserCommandFlowView:
    flow_id: str
    action_id: str
    user_label: str
    flow_status: str
    current_stage_id: str
    target_stage_id: str
    preferred_workspace_id: str
    preferred_panel_id: str
    requires_confirmation: bool = False
    dry_run_available: bool = False
    execute_allowed: bool = False
    closure_ready: bool = False
    reason_blocked: str | None = None
    steps: list[EndUserCommandFlowStepView] = field(default_factory=list)


@dataclass(frozen=True)
class EndUserCommandFlowViewModel:
    flow_status: str = "ready"
    source_role: str = "none"
    flows: list[EndUserCommandFlowView] = field(default_factory=list)
    enabled_flow_count: int = 0
    blocked_flow_count: int = 0
    recommended_flow_id: str | None = None
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


def _label_for(action_id: str, *, app_language: str) -> str:
    mapping = {
        "save_working_save": "Save draft",
        "review_draft": "Open review",
        "approve_for_commit": "Approve proposal",
        "request_revision": "Request revision",
        "commit_snapshot": "Commit snapshot",
        "run_current": "Run current",
        "cancel_run": "Cancel run",
        "replay_latest": "Replay latest",
        "open_diff": "Open diff",
    }
    return ui_text(f"builder.action.{action_id}", app_language=app_language, fallback_text=mapping.get(action_id, action_id.replace("_", " ").title()))


def _flow_status(*, execute_allowed: bool, requires_confirmation: bool, closure_ready: bool) -> str:
    if not execute_allowed:
        return "blocked"
    if requires_confirmation:
        return "confirmation_required"
    if closure_ready:
        return "ready"
    return "available"


def read_end_user_command_flow_view_model(
    source: SourceLike,
    *,
    execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None,
    explanation: str | None = None,
) -> EndUserCommandFlowViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    execution_adapter_hub = execution_adapter_hub or read_builder_execution_adapter_hub_view_model(source_unwrapped)

    adapters_by_action = {item.action_id: item for item in execution_adapter_hub.execution_adapters.adapters} if execution_adapter_hub.execution_adapters is not None else {}
    changes_by_action = {item.action_id: item for item in execution_adapter_hub.state_changes.changes} if execution_adapter_hub.state_changes is not None else {}
    routing_by_action = {item.action_id: item for item in execution_adapter_hub.dispatch_hub.interaction_hub.command_routing.routes} if execution_adapter_hub.dispatch_hub and execution_adapter_hub.dispatch_hub.interaction_hub and execution_adapter_hub.dispatch_hub.interaction_hub.command_routing else {}
    dispatch_by_action = {item.action_id: item for item in execution_adapter_hub.dispatch_hub.dispatch_contract.contracts} if execution_adapter_hub.dispatch_hub and execution_adapter_hub.dispatch_hub.dispatch_contract else {}
    intent_by_action = {item.action_id: item for item in execution_adapter_hub.dispatch_hub.intent_emission.emissions} if execution_adapter_hub.dispatch_hub and execution_adapter_hub.dispatch_hub.intent_emission else {}

    flows: list[EndUserCommandFlowView] = []
    for action_id, adapter in adapters_by_action.items():
        state_change = changes_by_action.get(action_id)
        route = routing_by_action.get(action_id)
        dispatch = dispatch_by_action.get(action_id)
        intent = intent_by_action.get(action_id)
        if state_change is None or route is None or dispatch is None:
            continue

        closure_ready = adapter.execute_allowed and state_change.apply_allowed
        steps = [
            EndUserCommandFlowStepView("intent", ui_text("flow.step.intent", app_language=app_language, fallback_text="Intent emission"), "ready" if intent is not None and intent.emit_allowed else "waiting", dispatch.command_type if dispatch is not None else "none"),
            EndUserCommandFlowStepView("dispatch", ui_text("flow.step.dispatch", app_language=app_language, fallback_text="Dispatch contract"), "ready" if dispatch.dispatch_allowed else "blocked", dispatch.boundary_target),
            EndUserCommandFlowStepView("execute", ui_text("flow.step.execute", app_language=app_language, fallback_text="Execution adapter"), "ready" if adapter.execute_allowed else "blocked", adapter.engine_boundary),
            EndUserCommandFlowStepView("state_change", ui_text("flow.step.state_change", app_language=app_language, fallback_text="UI state change"), "ready" if state_change.apply_allowed else "blocked", state_change.state_change_kind),
        ]
        flows.append(
            EndUserCommandFlowView(
                flow_id=f"flow:{action_id}",
                action_id=action_id,
                user_label=route.label or _label_for(action_id, app_language=app_language),
                flow_status=_flow_status(
                    execute_allowed=adapter.execute_allowed,
                    requires_confirmation=route.requires_confirmation,
                    closure_ready=closure_ready,
                ),
                current_stage_id=state_change.current_stage_id,
                target_stage_id=state_change.target_stage_id,
                preferred_workspace_id=state_change.target_workspace_id,
                preferred_panel_id=state_change.target_panel_id,
                requires_confirmation=route.requires_confirmation,
                dry_run_available=adapter.dry_run_available,
                execute_allowed=adapter.execute_allowed,
                closure_ready=closure_ready,
                reason_blocked=adapter.reason_blocked if not adapter.execute_allowed else None,
                steps=steps,
            )
        )

    enabled_flow_count = sum(1 for item in flows if item.execute_allowed)
    blocked_flow_count = len(flows) - enabled_flow_count
    if not flows:
        status = "empty"
    elif blocked_flow_count == len(flows):
        status = "blocked"
    elif blocked_flow_count:
        status = "attention"
    else:
        status = "ready"

    recommended_flow_id = None
    if execution_adapter_hub.dispatch_hub is not None and execution_adapter_hub.dispatch_hub.recommended_action_id is not None:
        recommended_flow_id = f"flow:{execution_adapter_hub.dispatch_hub.recommended_action_id}"

    return EndUserCommandFlowViewModel(
        flow_status=status,
        source_role=source_role,
        flows=flows,
        enabled_flow_count=enabled_flow_count,
        blocked_flow_count=blocked_flow_count,
        recommended_flow_id=recommended_flow_id,
        explanation=explanation,
    )


__all__ = [
    "EndUserCommandFlowStepView",
    "EndUserCommandFlowView",
    "EndUserCommandFlowViewModel",
    "read_end_user_command_flow_view_model",
]
