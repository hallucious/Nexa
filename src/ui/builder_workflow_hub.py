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
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.builder_shell import BuilderShellViewModel, read_builder_shell_view_model
from src.ui.execution_launch_workflow import ExecutionLaunchWorkflowViewModel, read_execution_launch_workflow_view_model
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.proposal_commit_workflow import ProposalCommitWorkflowViewModel, read_proposal_commit_workflow_view_model


@dataclass(frozen=True)
class BuilderWorkflowHubViewModel:
    hub_status: str = "ready"
    hub_status_label: str | None = None
    storage_role: str = "none"
    active_workflow_id: str = "proposal_commit"
    active_workflow_label: str | None = None
    recommended_workflow_id: str = "proposal_commit"
    recommended_workflow_label: str | None = None
    available_workflow_ids: list[str] = field(default_factory=lambda: ["proposal_commit", "execution_launch"])
    proposal_commit: ProposalCommitWorkflowViewModel | None = None
    execution_launch: ExecutionLaunchWorkflowViewModel | None = None
    shell: BuilderShellViewModel | None = None
    alert_count: int = 0
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


def read_builder_workflow_hub_view_model(
    source: SourceLike,
    *,
    selected_ref: str | None = None,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    live_events=None,
    selected_artifact_id: str | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> BuilderWorkflowHubViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    proposal_commit_vm = read_proposal_commit_workflow_view_model(
        source_unwrapped,
        selected_ref=selected_ref,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel)) else None

    execution_launch_vm = read_execution_launch_workflow_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        live_events=live_events,
        selected_artifact_id=selected_artifact_id,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    shell_vm = read_builder_shell_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        selected_ref=selected_ref,
        live_events=live_events,
        selected_artifact_id=selected_artifact_id,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    if execution_launch_vm is not None and execution_launch_vm.workflow_status == "live_monitoring":
        recommended = "execution_launch"
    elif storage_role == "commit_snapshot" and execution_launch_vm is not None and execution_launch_vm.workflow_status in {"launch_ready", "replay_ready"}:
        recommended = "execution_launch"
    elif proposal_commit_vm is not None and proposal_commit_vm.workflow_status in {"commit_ready", "awaiting_approval", "preview_ready", "proposal_in_progress"}:
        recommended = "proposal_commit"
    elif storage_role == "execution_record":
        recommended = "execution_launch"
    else:
        recommended = "proposal_commit"

    active = recommended
    if shell_vm is not None and shell_vm.shell_mode == "runtime_monitoring":
        active = "execution_launch"
    elif shell_vm is not None and shell_vm.shell_mode == "designer_review":
        active = "proposal_commit"

    alert_count = 0
    if proposal_commit_vm is not None:
        alert_count += proposal_commit_vm.summary.blocking_count + proposal_commit_vm.summary.pending_decision_count
    if execution_launch_vm is not None:
        alert_count += execution_launch_vm.summary.blocking_count

    if proposal_commit_vm is None and execution_launch_vm is None:
        hub_status = "empty"
    elif recommended == "execution_launch" and execution_launch_vm is not None:
        hub_status = execution_launch_vm.workflow_status
    elif recommended == "proposal_commit" and proposal_commit_vm is not None:
        hub_status = proposal_commit_vm.workflow_status
    else:
        hub_status = "ready"

    return BuilderWorkflowHubViewModel(
        hub_status=hub_status,
        hub_status_label=ui_text(f"hub.status.{hub_status}", app_language=app_language, fallback_text=hub_status.replace("_", " ")),
        storage_role=storage_role,
        active_workflow_id=active,
        active_workflow_label=ui_text(f"workflow.{active}", app_language=app_language, fallback_text=active.replace("_", " ")),
        recommended_workflow_id=recommended,
        recommended_workflow_label=ui_text(f"workflow.{recommended}", app_language=app_language, fallback_text=recommended.replace("_", " ")),
        proposal_commit=proposal_commit_vm,
        execution_launch=execution_launch_vm,
        shell=shell_vm,
        alert_count=alert_count,
        explanation=explanation,
    )


__all__ = ["BuilderWorkflowHubViewModel", "read_builder_workflow_hub_view_model"]
