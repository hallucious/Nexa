from __future__ import annotations

from dataclasses import dataclass

from src.contracts.nex_contract import ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.command_routing import BuilderCommandRoutingViewModel, read_builder_command_routing_view_model
from src.ui.interaction_transitions import BuilderInteractionTransitionViewModel, read_builder_interaction_transition_view_model


@dataclass(frozen=True)
class BuilderInteractionHubViewModel:
    hub_status: str = "ready"
    hub_status_label: str | None = None
    source_role: str = "none"
    workflow_hub: BuilderWorkflowHubViewModel | None = None
    command_routing: BuilderCommandRoutingViewModel | None = None
    interaction_transition: BuilderInteractionTransitionViewModel | None = None
    active_workspace_id: str = "visual_editor"
    active_workspace_label: str | None = None
    recommended_action_id: str | None = None
    enabled_command_count: int = 0
    pending_confirmation_count: int = 0
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


def read_builder_interaction_hub_view_model(
    source: SourceLike,
    *,
    selected_ref: str | None = None,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay=None,
    live_events=None,
    selected_artifact_id: str | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    selected_action_id: str | None = None,
    explanation: str | None = None,
) -> BuilderInteractionHubViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    workflow_hub = read_builder_workflow_hub_view_model(
        source_unwrapped,
        selected_ref=selected_ref,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        live_events=live_events,
        selected_artifact_id=selected_artifact_id,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    )
    command_routing = read_builder_command_routing_view_model(
        source_unwrapped,
        action_schema=workflow_hub.shell.action_schema if workflow_hub.shell is not None else None,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination if workflow_hub.shell is not None else None,
    )
    transition = read_builder_interaction_transition_view_model(
        source_unwrapped,
        command_routing=command_routing,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination if workflow_hub.shell is not None else None,
        selected_action_id=selected_action_id,
    )

    active_workspace_id = transition.current_workspace_id
    if workflow_hub.shell is not None and workflow_hub.shell.shell_mode == "runtime_monitoring":
        active_workspace_id = "runtime_monitoring"
    elif workflow_hub.shell is not None and workflow_hub.shell.shell_mode == "designer_review":
        active_workspace_id = "node_configuration"

    pending_confirmation_count = sum(1 for route in command_routing.routes if route.enabled and route.requires_confirmation)
    if command_routing.routing_status == "empty":
        hub_status = "empty"
    elif workflow_hub.hub_status == "terminal" and transition.transition_status != "blocked":
        hub_status = "terminal"
    elif workflow_hub.hub_status == "blocked" or transition.transition_status == "blocked" or command_routing.routing_status == "blocked":
        hub_status = "blocked"
    elif workflow_hub.alert_count or workflow_hub.hub_status == "attention" or pending_confirmation_count or command_routing.routing_status == "attention":
        hub_status = "attention"
    else:
        hub_status = "ready"

    return BuilderInteractionHubViewModel(
        hub_status=hub_status,
        hub_status_label=ui_text(f"hub.status.{hub_status}", app_language=app_language, fallback_text=hub_status.replace("_", " ")),
        source_role=source_role,
        workflow_hub=workflow_hub,
        command_routing=command_routing,
        interaction_transition=transition,
        active_workspace_id=active_workspace_id,
        active_workspace_label=ui_text(f"workspace.{active_workspace_id}.name", app_language=app_language, fallback_text=active_workspace_id.replace("_", " ")),
        recommended_action_id=transition.recommended_action_id,
        enabled_command_count=command_routing.enabled_route_count,
        pending_confirmation_count=pending_confirmation_count,
        explanation=explanation,
    )


__all__ = [
    "BuilderInteractionHubViewModel",
    "read_builder_interaction_hub_view_model",
]
