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
from src.ui.builder_end_user_flow_hub import BuilderEndUserFlowHubViewModel, read_builder_end_user_flow_hub_view_model
from src.ui.execution_launch_workflow import ExecutionLaunchWorkflowViewModel, read_execution_launch_workflow_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.product_flow_gateway import ProductFlowGatewayViewModel, read_product_flow_gateway_view_model
from src.ui.proposal_commit_workflow import ProposalCommitWorkflowViewModel, read_proposal_commit_workflow_view_model


@dataclass(frozen=True)
class ProductFlowE2EProofCheckpointView:
    checkpoint_id: str
    label: str
    checkpoint_status: str
    checkpoint_status_label: str
    proven: bool = False
    actionable: bool = False
    blocked: bool = False
    live: bool = False
    required_action_id: str | None = None
    required_action_label: str | None = None
    next_step_label: str | None = None
    evidence_ref: str | None = None
    boundary_ref: str | None = None


@dataclass(frozen=True)
class ProductFlowE2EProofViewModel:
    proof_status: str = "empty"
    proof_status_label: str | None = None
    source_role: str = "none"
    current_checkpoint_id: str | None = None
    recommended_checkpoint_id: str | None = None
    live_checkpoint_id: str | None = None
    overall_proven: bool = False
    proven_checkpoint_count: int = 0
    actionable_checkpoint_count: int = 0
    blocked_checkpoint_count: int = 0
    open_checkpoint_count: int = 0
    checkpoints: list[ProductFlowE2EProofCheckpointView] = field(default_factory=list)
    proposal_commit: ProposalCommitWorkflowViewModel | None = None
    execution_launch: ExecutionLaunchWorkflowViewModel | None = None
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None
    gateway: ProductFlowGatewayViewModel | None = None
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


def _checkpoint_label(checkpoint_id: str, *, app_language: str) -> str:
    fallbacks = {
        "review": "Review proof",
        "commit": "Commit proof",
        "run": "Run proof",
        "followthrough": "Follow-through proof",
    }
    return ui_text(f"proof.checkpoint.{checkpoint_id}", app_language=app_language, fallback_text=fallbacks[checkpoint_id])


def _status_label(status: str, *, app_language: str) -> str:
    return ui_text(f"proof.status.{status}", app_language=app_language, fallback_text=status.replace("_", " ").title())


def _action_label(action_id: str | None, *, app_language: str) -> str | None:
    if action_id is None:
        return None
    return ui_text(f"builder.action.{action_id}", app_language=app_language, fallback_text=action_id.replace("_", " ").title())


def _stage_status(*, proven: bool, live: bool, blocked: bool, actionable: bool, open_state: bool) -> str:
    if live:
        return "live"
    if proven:
        return "proven"
    if blocked:
        return "blocked"
    if actionable:
        return "actionable"
    if open_state:
        return "open"
    return "idle"




def _preferred_followthrough_action(execution: ExecutionLaunchWorkflowViewModel | None, *, source_role: str) -> str | None:
    if execution is None:
        return None
    trace_action = execution.action_state.trace_action
    artifact_action = execution.action_state.artifact_action
    compare_action = execution.action_state.compare_action
    replay_action = execution.action_state.replay_action
    has_trace = execution.summary.visible_event_count > 0
    has_artifacts = execution.summary.visible_artifact_count > 0
    has_run = execution.summary.run_id is not None or source_role == "execution_record"
    ordered = [trace_action if has_trace else None, artifact_action if has_artifacts else None, compare_action if has_run else None, replay_action if has_run else None]
    for action in ordered:
        if action is not None and action.enabled:
            return action.action_id
    return None

def _review_checkpoint(proposal: ProposalCommitWorkflowViewModel | None, *, app_language: str) -> ProductFlowE2EProofCheckpointView:
    review_action = proposal.action_state.review_action if proposal is not None else None
    open_state = bool(
        proposal is not None
        and (
            proposal.summary.current_intent_id is not None
            or proposal.summary.current_patch_id is not None
            or proposal.summary.current_preview_id is not None
            or proposal.summary.current_approval_id is not None
        )
    )
    proven = bool(
        proposal is not None
        and (
            proposal.summary.current_preview_id is not None
            or proposal.summary.current_approval_id is not None
            or proposal.workflow_status in {"awaiting_approval", "commit_ready", "committed_context", "historical_context"}
        )
    )
    actionable = bool(review_action is not None and review_action.enabled and not proven)
    blocked = bool(proposal is not None and proposal.workflow_status == "blocked" and not proven)
    status = _stage_status(proven=proven, live=False, blocked=blocked, actionable=actionable, open_state=open_state)
    return ProductFlowE2EProofCheckpointView(
        checkpoint_id="review",
        label=_checkpoint_label("review", app_language=app_language),
        checkpoint_status=status,
        checkpoint_status_label=_status_label(status, app_language=app_language),
        proven=proven,
        actionable=actionable,
        blocked=blocked,
        required_action_id=(review_action.action_id if review_action is not None and actionable else None),
        required_action_label=_action_label(review_action.action_id if review_action is not None and actionable else None, app_language=app_language),
        next_step_label=(proposal.summary.next_step_label if proposal is not None else None),
        evidence_ref=(proposal.summary.current_preview_id if proposal is not None else None) or (proposal.summary.current_approval_id if proposal is not None else None) or (proposal.summary.current_intent_id if proposal is not None else None),
        boundary_ref="proposal_commit_workflow",
    )


def _commit_checkpoint(proposal: ProposalCommitWorkflowViewModel | None, execution: ExecutionLaunchWorkflowViewModel | None, execution_record: ExecutionRecordModel | None, source_role: str, *, app_language: str) -> ProductFlowE2EProofCheckpointView:
    commit_action = proposal.action_state.commit_action if proposal is not None else None
    approve_action = proposal.action_state.approve_action if proposal is not None else None
    commit_evidence_ref = None
    if execution is not None and execution.summary.commit_anchor_ref is not None:
        commit_evidence_ref = execution.summary.commit_anchor_ref
    elif execution_record is not None and execution_record.source.commit_id:
        commit_evidence_ref = f"commit_snapshot:{execution_record.source.commit_id}"
    elif source_role == "commit_snapshot":
        commit_evidence_ref = "commit_snapshot:current"
    elif source_role == "execution_record":
        commit_evidence_ref = "commit_snapshot:anchored"

    proven = commit_evidence_ref is not None
    open_state = bool(proposal is not None and (proposal.summary.current_preview_id is not None or proposal.summary.current_approval_id is not None))
    actionable = bool(
        not proven
        and (
            (commit_action is not None and commit_action.enabled)
            or (approve_action is not None and approve_action.enabled)
        )
    )
    blocked = bool(proposal is not None and proposal.workflow_status == "blocked" and not proven)
    required_action_id = None
    if not proven:
        if commit_action is not None and commit_action.enabled:
            required_action_id = commit_action.action_id
        elif approve_action is not None and approve_action.enabled:
            required_action_id = approve_action.action_id
    status = _stage_status(proven=proven, live=False, blocked=blocked, actionable=actionable, open_state=open_state)
    return ProductFlowE2EProofCheckpointView(
        checkpoint_id="commit",
        label=_checkpoint_label("commit", app_language=app_language),
        checkpoint_status=status,
        checkpoint_status_label=_status_label(status, app_language=app_language),
        proven=proven,
        actionable=actionable,
        blocked=blocked,
        required_action_id=required_action_id,
        required_action_label=_action_label(required_action_id, app_language=app_language),
        next_step_label=(proposal.summary.next_step_label if proposal is not None else None),
        evidence_ref=commit_evidence_ref or (proposal.summary.current_approval_id if proposal is not None else None),
        boundary_ref="commit_boundary",
    )


def _run_checkpoint(execution: ExecutionLaunchWorkflowViewModel | None, source_role: str, *, app_language: str) -> ProductFlowE2EProofCheckpointView:
    run_action = execution.action_state.run_action if execution is not None else None
    live = bool(execution is not None and execution.workflow_status == "live_monitoring")
    run_evidence_ref = None
    if execution is not None and execution.summary.run_id is not None:
        run_evidence_ref = f"execution_record:{execution.summary.run_id}"
    elif source_role == "execution_record":
        run_evidence_ref = "execution_record:current"
    proven = run_evidence_ref is not None
    open_state = bool(execution is not None and execution.summary.commit_anchor_ref is not None)
    actionable = bool(run_action is not None and run_action.enabled and not proven and not live)
    blocked = bool(execution is not None and execution.workflow_status == "blocked" and not proven and not live)
    status = _stage_status(proven=proven, live=live, blocked=blocked, actionable=actionable, open_state=open_state)
    return ProductFlowE2EProofCheckpointView(
        checkpoint_id="run",
        label=_checkpoint_label("run", app_language=app_language),
        checkpoint_status=status,
        checkpoint_status_label=_status_label(status, app_language=app_language),
        proven=proven,
        actionable=actionable,
        blocked=blocked,
        live=live,
        required_action_id=(run_action.action_id if run_action is not None and actionable else None),
        required_action_label=_action_label(run_action.action_id if run_action is not None and actionable else None, app_language=app_language),
        next_step_label=(execution.summary.next_step_label if execution is not None else None),
        evidence_ref=run_evidence_ref or (execution.summary.commit_anchor_ref if execution is not None else None),
        boundary_ref="execution_launch_workflow",
    )


def _followthrough_checkpoint(execution: ExecutionLaunchWorkflowViewModel | None, source_role: str, *, app_language: str) -> ProductFlowE2EProofCheckpointView:
    event_count = execution.summary.visible_event_count if execution is not None else 0
    artifact_count = execution.summary.visible_artifact_count if execution is not None else 0
    run_id = execution.summary.run_id if execution is not None else None
    evidence_present = bool(run_id is not None and (event_count > 0 or artifact_count > 0)) or (source_role == "execution_record" and (event_count > 0 or artifact_count > 0 or run_id is not None))
    proven = evidence_present
    open_state = bool(run_id is not None or source_role == "execution_record")
    required_action_id = _preferred_followthrough_action(execution, source_role=source_role)
    actionable = bool(required_action_id is not None)
    blocked = False
    status = _stage_status(proven=proven, live=False, blocked=blocked, actionable=actionable and not proven, open_state=open_state)
    return ProductFlowE2EProofCheckpointView(
        checkpoint_id="followthrough",
        label=_checkpoint_label("followthrough", app_language=app_language),
        checkpoint_status=status,
        checkpoint_status_label=_status_label(status, app_language=app_language),
        proven=proven,
        actionable=bool(actionable and not proven),
        blocked=blocked,
        required_action_id=required_action_id,
        required_action_label=_action_label(required_action_id, app_language=app_language),
        next_step_label=(execution.summary.next_step_label if execution is not None else None),
        evidence_ref=(f"execution_record:{run_id}" if run_id is not None else None),
        boundary_ref="followthrough_inspection",
    )


def read_product_flow_e2e_proof_view_model(
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
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None,
    gateway: ProductFlowGatewayViewModel | None = None,
    explanation: str | None = None,
) -> ProductFlowE2EProofViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    if source_unwrapped is None and execution_record is None:
        return ProductFlowE2EProofViewModel()

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
    end_user_flow_hub = end_user_flow_hub or read_builder_end_user_flow_hub_view_model(base_source)
    gateway = gateway or read_product_flow_gateway_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        proposal_commit=proposal_commit,
        execution_launch=execution_launch,
    )

    checkpoints = [
        _review_checkpoint(proposal_commit, app_language=app_language),
        _commit_checkpoint(proposal_commit, execution_launch, execution_record, source_role, app_language=app_language),
        _run_checkpoint(execution_launch, source_role, app_language=app_language),
        _followthrough_checkpoint(execution_launch, source_role, app_language=app_language),
    ]

    live_checkpoint = next((item for item in checkpoints if item.live), None)
    first_blocked = next((item for item in checkpoints if item.blocked), None)
    first_actionable = next((item for item in checkpoints if item.actionable), None)
    first_open = next((item for item in checkpoints if item.checkpoint_status == "open"), None)
    last_proven = next((item for item in reversed(checkpoints) if item.proven), None)

    proven_count = sum(1 for item in checkpoints if item.proven)
    actionable_count = sum(1 for item in checkpoints if item.actionable)
    blocked_count = sum(1 for item in checkpoints if item.blocked)
    open_count = sum(1 for item in checkpoints if item.checkpoint_status == "open")
    overall_proven = all(item.proven for item in checkpoints)

    if live_checkpoint is not None:
        proof_status = "live"
        current_checkpoint = live_checkpoint
        recommended_checkpoint = live_checkpoint
    elif overall_proven:
        proof_status = "proven"
        current_checkpoint = last_proven
        recommended_checkpoint = last_proven
    elif first_blocked is not None and actionable_count == 0:
        proof_status = "blocked"
        current_checkpoint = first_blocked
        recommended_checkpoint = first_blocked
    elif first_actionable is not None:
        proof_status = "actionable" if proven_count else "partial"
        current_checkpoint = first_actionable
        recommended_checkpoint = first_actionable
    elif first_open is not None:
        proof_status = "partial"
        current_checkpoint = first_open
        recommended_checkpoint = first_open
    elif last_proven is not None:
        proof_status = "partial"
        current_checkpoint = last_proven
        recommended_checkpoint = last_proven
    else:
        proof_status = "idle"
        current_checkpoint = checkpoints[0] if checkpoints else None
        recommended_checkpoint = current_checkpoint

    return ProductFlowE2EProofViewModel(
        proof_status=proof_status,
        proof_status_label=_status_label(proof_status, app_language=app_language),
        source_role=source_role,
        current_checkpoint_id=(current_checkpoint.checkpoint_id if current_checkpoint is not None else None),
        recommended_checkpoint_id=(recommended_checkpoint.checkpoint_id if recommended_checkpoint is not None else None),
        live_checkpoint_id=(live_checkpoint.checkpoint_id if live_checkpoint is not None else None),
        overall_proven=(proof_status == "proven"),
        proven_checkpoint_count=proven_count,
        actionable_checkpoint_count=actionable_count,
        blocked_checkpoint_count=blocked_count,
        open_checkpoint_count=open_count,
        checkpoints=checkpoints,
        proposal_commit=proposal_commit,
        execution_launch=execution_launch,
        end_user_flow_hub=end_user_flow_hub,
        gateway=gateway,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowE2EProofCheckpointView",
    "ProductFlowE2EProofViewModel",
    "read_product_flow_e2e_proof_view_model",
]
