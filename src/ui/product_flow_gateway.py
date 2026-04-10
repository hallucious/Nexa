from __future__ import annotations

from dataclasses import dataclass, field

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
from src.ui.execution_launch_workflow import ExecutionLaunchWorkflowViewModel, read_execution_launch_workflow_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.proposal_commit_workflow import ProposalCommitWorkflowViewModel, read_proposal_commit_workflow_view_model


@dataclass(frozen=True)
class ProductFlowGatewayStageView:
    gateway_id: str
    label: str
    gateway_status: str
    gateway_status_label: str
    open: bool = False
    actionable: bool = False
    live: bool = False
    boundary_ready: bool = False
    required_action_id: str | None = None
    required_action_label: str | None = None
    next_step_label: str | None = None
    target_ref: str | None = None


@dataclass(frozen=True)
class ProductFlowGatewayViewModel:
    gateway_status: str = "empty"
    gateway_status_label: str | None = None
    source_role: str = "none"
    current_gateway_id: str | None = None
    recommended_gateway_id: str | None = None
    live_gateway_id: str | None = None
    boundary_ready_count: int = 0
    actionable_gateway_count: int = 0
    blocked_gateway_count: int = 0
    stages: list[ProductFlowGatewayStageView] = field(default_factory=list)
    proposal_commit: ProposalCommitWorkflowViewModel | None = None
    execution_launch: ExecutionLaunchWorkflowViewModel | None = None
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


def _action_label(action_id: str | None, *, app_language: str) -> str | None:
    if action_id is None:
        return None
    return ui_text(f"builder.action.{action_id}", app_language=app_language, fallback_text=action_id.replace("_", " ").title())


def _stage_label(gateway_id: str, *, app_language: str) -> str:
    fallbacks = {
        "review": "Review gateway",
        "commit": "Commit gateway",
        "run": "Run gateway",
        "followthrough": "Follow-through gateway",
    }
    return ui_text(f"gateway.stage.{gateway_id}", app_language=app_language, fallback_text=fallbacks[gateway_id])


def _status_label(status: str, *, app_language: str) -> str:
    return ui_text(f"gateway.status.{status}", app_language=app_language, fallback_text=status.replace("_", " ").title())


def _review_stage(proposal: ProposalCommitWorkflowViewModel | None, *, app_language: str) -> ProductFlowGatewayStageView:
    action = proposal.action_state.review_action if proposal is not None else None
    proposal_in_flight = bool(proposal is not None and (proposal.summary.current_preview_id is not None or proposal.summary.current_approval_id is not None))
    open_state = bool(proposal is not None and proposal.summary.current_intent_id is not None)
    actionable = bool(action is not None and action.enabled and not proposal_in_flight)
    blocked = bool(proposal is not None and proposal.summary.blocking_count > 0 and not actionable)
    boundary_ready = bool(proposal is not None and (proposal.can_review or proposal.summary.current_preview_id is not None or proposal.summary.current_approval_id is not None))
    if blocked:
        status = "blocked"
    elif actionable:
        status = "actionable"
    elif open_state:
        status = "open"
    elif boundary_ready:
        status = "ready"
    else:
        status = "idle"
    return ProductFlowGatewayStageView(
        gateway_id="review",
        label=_stage_label("review", app_language=app_language),
        gateway_status=status,
        gateway_status_label=_status_label(status, app_language=app_language),
        open=open_state,
        actionable=actionable,
        boundary_ready=boundary_ready,
        required_action_id=(action.action_id if action is not None else None),
        required_action_label=_action_label(action.action_id if action is not None else None, app_language=app_language),
        next_step_label=(proposal.summary.next_step_label if proposal is not None else None),
        target_ref=(proposal.summary.current_preview_id if proposal is not None else None),
    )


def _commit_stage(proposal: ProposalCommitWorkflowViewModel | None, *, app_language: str) -> ProductFlowGatewayStageView:
    action = proposal.action_state.commit_action if proposal is not None else None
    approval = proposal.action_state.approve_action if proposal is not None else None
    open_state = bool(proposal is not None and (proposal.summary.current_preview_id is not None or proposal.summary.current_approval_id is not None))
    actionable = bool(action is not None and action.enabled)
    needs_approval = bool(not actionable and approval is not None and approval.enabled)
    blocked = bool(proposal is not None and proposal.summary.blocking_count > 0 and not actionable and not needs_approval)
    boundary_ready = bool(proposal is not None and proposal.summary.commit_eligible)
    if blocked:
        status = "blocked"
    elif actionable:
        status = "actionable"
    elif needs_approval:
        status = "open"
    elif boundary_ready:
        status = "ready"
    elif open_state:
        status = "open"
    else:
        status = "idle"
    required_action_id = (action.action_id if action is not None and action.enabled else None) or (approval.action_id if approval is not None and approval.enabled else None)
    return ProductFlowGatewayStageView(
        gateway_id="commit",
        label=_stage_label("commit", app_language=app_language),
        gateway_status=status,
        gateway_status_label=_status_label(status, app_language=app_language),
        open=open_state,
        actionable=actionable or needs_approval,
        boundary_ready=boundary_ready,
        required_action_id=required_action_id,
        required_action_label=_action_label(required_action_id, app_language=app_language),
        next_step_label=(proposal.summary.next_step_label if proposal is not None else None),
        target_ref=(proposal.summary.current_approval_id if proposal is not None else None),
    )


def _run_stage(execution: ExecutionLaunchWorkflowViewModel | None, *, app_language: str) -> ProductFlowGatewayStageView:
    run_action = execution.action_state.run_action if execution is not None else None
    live = bool(execution is not None and execution.workflow_status == "live_monitoring")
    actionable = bool(run_action is not None and run_action.enabled)
    blocked = bool(execution is not None and execution.summary.blocking_count > 0 and not actionable and not live)
    boundary_ready = bool(execution is not None and (execution.can_launch or execution.summary.commit_anchor_ref is not None))
    open_state = bool(execution is not None and execution.summary.commit_anchor_ref is not None)
    if live:
        status = "live"
    elif blocked:
        status = "blocked"
    elif actionable:
        status = "actionable"
    elif boundary_ready:
        status = "ready"
    elif open_state:
        status = "open"
    else:
        status = "idle"
    return ProductFlowGatewayStageView(
        gateway_id="run",
        label=_stage_label("run", app_language=app_language),
        gateway_status=status,
        gateway_status_label=_status_label(status, app_language=app_language),
        open=open_state,
        actionable=actionable,
        live=live,
        boundary_ready=boundary_ready,
        required_action_id=(run_action.action_id if run_action is not None else None),
        required_action_label=_action_label(run_action.action_id if run_action is not None else None, app_language=app_language),
        next_step_label=(execution.summary.next_step_label if execution is not None else None),
        target_ref=(execution.summary.commit_anchor_ref if execution is not None else None),
    )


def _followthrough_stage(execution: ExecutionLaunchWorkflowViewModel | None, *, app_language: str) -> ProductFlowGatewayStageView:
    compare_action = execution.action_state.compare_action if execution is not None else None
    replay_action = execution.action_state.replay_action if execution is not None else None
    has_outputs = bool(execution is not None and (execution.summary.visible_event_count > 0 or execution.summary.visible_artifact_count > 0 or execution.summary.run_id is not None))
    actionable = bool((compare_action is not None and compare_action.enabled) or (replay_action is not None and replay_action.enabled))
    live = bool(execution is not None and execution.workflow_status == "live_monitoring")
    boundary_ready = has_outputs
    if live:
        status = "live"
    elif actionable:
        status = "actionable"
    elif boundary_ready:
        status = "ready"
    else:
        status = "idle"
    required_action_id = (compare_action.action_id if compare_action is not None and compare_action.enabled else None) or (replay_action.action_id if replay_action is not None and replay_action.enabled else None)
    return ProductFlowGatewayStageView(
        gateway_id="followthrough",
        label=_stage_label("followthrough", app_language=app_language),
        gateway_status=status,
        gateway_status_label=_status_label(status, app_language=app_language),
        open=has_outputs,
        actionable=actionable,
        live=live,
        boundary_ready=boundary_ready,
        required_action_id=required_action_id,
        required_action_label=_action_label(required_action_id, app_language=app_language),
        next_step_label=(execution.summary.next_step_label if execution is not None else None),
        target_ref=(execution.summary.run_id if execution is not None else None),
    )


def read_product_flow_gateway_view_model(
    source: SourceLike,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    proposal_commit: ProposalCommitWorkflowViewModel | None = None,
    execution_launch: ExecutionLaunchWorkflowViewModel | None = None,
    explanation: str | None = None,
) -> ProductFlowGatewayViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    if source_unwrapped is None and execution_record is None:
        return ProductFlowGatewayViewModel()

    base_source = source_unwrapped if source_unwrapped is not None else execution_record
    proposal_commit = proposal_commit or (
        read_proposal_commit_workflow_view_model(
            base_source,
            validation_report=validation_report,
            execution_record=execution_record,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
        )
        if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel))
        else None
    )
    execution_launch = execution_launch or read_execution_launch_workflow_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
    )

    stages = [
        _review_stage(proposal_commit, app_language=app_language),
        _commit_stage(proposal_commit, app_language=app_language),
        _run_stage(execution_launch, app_language=app_language),
        _followthrough_stage(execution_launch, app_language=app_language),
    ]

    stage_by_id = {stage.gateway_id: stage for stage in stages}
    review_stage = stage_by_id.get("review")
    commit_stage = stage_by_id.get("commit")
    run_stage = stage_by_id.get("run")
    followthrough_stage = stage_by_id.get("followthrough")
    live_stage = next((stage for stage in stages if stage.live), None)
    blocked_stage = next((stage for stage in stages if stage.gateway_status == "blocked"), None)

    if live_stage is not None:
        gateway_status = "live"
        current_stage = live_stage
        recommended_stage = live_stage
    elif source_role == "execution_record" and followthrough_stage is not None and followthrough_stage.boundary_ready:
        gateway_status = "actionable" if followthrough_stage.actionable else "ready"
        current_stage = followthrough_stage
        recommended_stage = followthrough_stage
    elif source_role == "execution_record" and run_stage is not None and run_stage.boundary_ready:
        gateway_status = "actionable" if run_stage.actionable else "ready"
        current_stage = run_stage
        recommended_stage = run_stage
    elif source_role == "commit_snapshot" and run_stage is not None and run_stage.boundary_ready:
        gateway_status = "actionable" if run_stage.actionable else "ready"
        current_stage = run_stage
        recommended_stage = run_stage
    elif commit_stage is not None and commit_stage.gateway_status in {"actionable", "open", "ready"} and commit_stage.open:
        gateway_status = "actionable" if commit_stage.actionable else "ready"
        current_stage = commit_stage
        recommended_stage = commit_stage
    elif followthrough_stage is not None and followthrough_stage.boundary_ready:
        gateway_status = "actionable" if followthrough_stage.actionable else "ready"
        current_stage = followthrough_stage
        recommended_stage = followthrough_stage
    elif run_stage is not None and run_stage.gateway_status in {"actionable", "ready", "open"} and run_stage.boundary_ready:
        gateway_status = "actionable" if run_stage.actionable else "ready"
        current_stage = run_stage
        recommended_stage = run_stage
    elif review_stage is not None and review_stage.gateway_status in {"actionable", "open", "ready"}:
        gateway_status = "actionable" if review_stage.actionable else "ready"
        current_stage = review_stage
        recommended_stage = review_stage
    elif blocked_stage is not None:
        gateway_status = "blocked"
        current_stage = blocked_stage
        recommended_stage = blocked_stage
    else:
        gateway_status = "idle"
        current_stage = stages[0] if stages else None
        recommended_stage = current_stage

    return ProductFlowGatewayViewModel(
        gateway_status=gateway_status,
        gateway_status_label=_status_label(gateway_status, app_language=app_language),
        source_role=source_role,
        current_gateway_id=(current_stage.gateway_id if current_stage is not None else None),
        recommended_gateway_id=(recommended_stage.gateway_id if recommended_stage is not None else None),
        live_gateway_id=(live_stage.gateway_id if live_stage is not None else None),
        boundary_ready_count=sum(1 for stage in stages if stage.boundary_ready),
        actionable_gateway_count=sum(1 for stage in stages if stage.actionable),
        blocked_gateway_count=sum(1 for stage in stages if stage.gateway_status == "blocked"),
        stages=stages,
        proposal_commit=proposal_commit,
        execution_launch=execution_launch,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowGatewayStageView",
    "ProductFlowGatewayViewModel",
    "read_product_flow_gateway_view_model",
]
