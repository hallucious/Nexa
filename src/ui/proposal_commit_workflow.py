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
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.designer_panel import DesignerPanelViewModel
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.node_configuration_workspace import NodeConfigurationWorkspaceViewModel, read_node_configuration_workspace_view_model
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model
from src.ui.visual_editor_workspace import VisualEditorWorkspaceViewModel, read_visual_editor_workspace_view_model
from src.ui.i18n import beginner_language_enabled, ui_language_from_sources, ui_text


@dataclass(frozen=True)
class ProposalCommitSummaryView:
    current_intent_id: str | None = None
    current_patch_id: str | None = None
    current_preview_id: str | None = None
    current_approval_id: str | None = None
    current_stage: str | None = None
    blocking_count: int = 0
    warning_count: int = 0
    confirmation_count: int = 0
    pending_decision_count: int = 0
    requires_confirmation: bool = False
    commit_eligible: bool = False
    next_step_label: str | None = None


@dataclass(frozen=True)
class ProposalCommitActionStateView:
    review_action: BuilderActionView | None = None
    commit_action: BuilderActionView | None = None
    approve_action: BuilderActionView | None = None
    request_revision_action: BuilderActionView | None = None
    compare_action: BuilderActionView | None = None


@dataclass(frozen=True)
class BeginnerProposalConfirmationView:
    visible: bool = False
    title: str | None = None
    summary: str | None = None
    prompt: str | None = None
    primary_action_label: str | None = None
    secondary_action_label: str | None = None


@dataclass(frozen=True)
class ProposalCommitWorkflowViewModel:
    workflow_status: str = "ready"
    storage_role: str = "none"
    beginner_mode: bool = False
    visual_editor: VisualEditorWorkspaceViewModel | None = None
    node_configuration: NodeConfigurationWorkspaceViewModel | None = None
    storage: StoragePanelViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    designer: DesignerPanelViewModel | None = None
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    summary: ProposalCommitSummaryView = field(default_factory=ProposalCommitSummaryView)
    action_state: ProposalCommitActionStateView = field(default_factory=ProposalCommitActionStateView)
    beginner_confirmation: BeginnerProposalConfirmationView = field(default_factory=BeginnerProposalConfirmationView)
    hide_internal_governance_by_default: bool = False
    can_review: bool = False
    can_commit: bool = False
    can_compare_to_commit: bool = False
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


def _find_action(action_schema: BuilderActionSchemaView, action_id: str) -> BuilderActionView | None:
    for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]:
        if action.action_id == action_id:
            return action
    return None


def _preferred_compare_action(action_schema: BuilderActionSchemaView, *, storage_role: str) -> BuilderActionView | None:
    if storage_role == "execution_record":
        priority = ["open_trace", "open_artifacts", "compare_runs", "open_latest_run", "open_diff"]
    elif storage_role == "commit_snapshot":
        priority = ["compare_runs", "open_diff", "open_latest_run", "open_trace", "open_artifacts"]
    else:
        priority = ["open_diff", "compare_runs"]
    fallback: BuilderActionView | None = None
    for action_id in priority:
        action = _find_action(action_schema, action_id)
        if action is None:
            continue
        if action.enabled:
            return action
        if fallback is None:
            fallback = action
    return fallback




def _beginner_confirmation(
    *,
    source,
    execution_record: ExecutionRecordModel | None,
    preview: CircuitDraftPreview | None,
    patch_plan: CircuitPatchPlan | None,
    intent: DesignerIntent | None,
    approve_action: BuilderActionView | None,
    request_revision_action: BuilderActionView | None,
    app_language: str,
) -> BeginnerProposalConfirmationView:
    if not beginner_language_enabled(source, execution_record):
        return BeginnerProposalConfirmationView()
    summary: str | None = None
    if preview is not None and getattr(preview, "summary_card", None) is not None:
        summary = preview.summary_card.one_sentence_summary
    elif patch_plan is not None and patch_plan.summary:
        summary = patch_plan.summary
    elif intent is not None and intent.explanation:
        summary = intent.explanation
    elif intent is not None and intent.objective.primary_goal:
        summary = intent.objective.primary_goal
    if summary is None:
        return BeginnerProposalConfirmationView()
    return BeginnerProposalConfirmationView(
        visible=True,
        title=ui_text("proposal.beginner.title", app_language=app_language),
        summary=summary,
        prompt=ui_text("proposal.beginner.prompt", app_language=app_language),
        primary_action_label=(ui_text("proposal.beginner.action.approve", app_language=app_language) if approve_action is not None else None),
        secondary_action_label=(ui_text("proposal.beginner.action.revise", app_language=app_language) if request_revision_action is not None else None),
    )

def read_proposal_commit_workflow_view_model(
    source: SourceLike,
    *,
    selected_ref: str | None = None,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> ProposalCommitWorkflowViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)
    beginner_mode = beginner_language_enabled(source_unwrapped, execution_record)

    storage_vm = read_storage_view_model(
        source_unwrapped,
        latest_execution_record=(execution_record if execution_record is not None and not isinstance(source_unwrapped, ExecutionRecordModel) else None),
    ) if source_unwrapped is not None else None
    validation_vm = (
        read_validation_panel_view_model(source_unwrapped, validation_report=validation_report, precheck=precheck, execution_record=execution_record)
        if source_unwrapped is not None
        else None
    )
    visual_editor_vm = (
        read_visual_editor_workspace_view_model(source_unwrapped, validation_report=validation_report, execution_record=execution_record, preview_overlay=preview_overlay)
        if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel))
        else None
    )
    node_config_vm = (
        read_node_configuration_workspace_view_model(
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
        )
        if source_unwrapped is not None
        else None
    )

    designer_vm = node_config_vm.designer if node_config_vm is not None else None
    action_schema = read_builder_action_schema(
        source_unwrapped,
        storage_view=storage_vm,
        validation_view=validation_vm,
        designer_view=designer_vm,
    )

    review_action = _find_action(action_schema, "review_draft")
    commit_action = _find_action(action_schema, "commit_snapshot")
    approve_action = _find_action(action_schema, "approve_for_commit")
    request_revision_action = _find_action(action_schema, "request_revision")
    compare_action = _preferred_compare_action(action_schema, storage_role=storage_role)

    preview_state = designer_vm.preview_state if designer_vm is not None else None
    approval_state = designer_vm.approval_state if designer_vm is not None else None
    precheck_state = designer_vm.precheck_state if designer_vm is not None else None
    intent_state = designer_vm.intent_state if designer_vm is not None else None
    patch_state = designer_vm.patch_state if designer_vm is not None else None

    has_precheck = precheck_state is not None and precheck_state.precheck_id is not None
    has_preview = preview_state is not None and preview_state.preview_id is not None
    has_approval = approval_state is not None and approval_state.approval_id is not None
    has_intent = intent_state is not None and intent_state.intent_id is not None

    next_step_label = None
    if has_precheck and precheck_state is not None and precheck_state.overall_status == "blocked":
        next_step_label = ui_text("proposal.next.resolve_blocking", app_language=app_language, fallback_text="Resolve blocking findings")
    elif has_approval and approval_state is not None and approval_state.commit_eligible:
        next_step_label = ui_text("proposal.next.commit_snapshot", app_language=app_language, fallback_text="Commit snapshot")
    elif has_preview and preview_state is not None:
        next_step_label = ui_text("proposal.next.review_preview", app_language=app_language, fallback_text="Review preview and approval state")
    elif has_intent and intent_state is not None:
        next_step_label = ui_text("proposal.next.generate_patch", app_language=app_language, fallback_text="Generate patch and preview")
    elif storage_role == "commit_snapshot":
        launch_action = _find_action(action_schema, "run_from_commit")
        if launch_action is not None and launch_action.enabled:
            next_step_label = launch_action.label
        elif compare_action is not None and compare_action.enabled:
            next_step_label = compare_action.label
    elif storage_role == "execution_record":
        if compare_action is not None and compare_action.enabled:
            next_step_label = compare_action.label
    elif storage_role == "working_save":
        next_step_label = ui_text("proposal.next.start_designer", app_language=app_language, fallback_text="Start a designer proposal or review current draft")

    summary = ProposalCommitSummaryView(
        current_intent_id=intent_state.intent_id if has_intent and intent_state is not None else None,
        current_patch_id=patch_state.patch_id if patch_state is not None and patch_state.patch_id is not None else None,
        current_preview_id=preview_state.preview_id if has_preview and preview_state is not None else None,
        current_approval_id=approval_state.approval_id if has_approval and approval_state is not None else None,
        current_stage=approval_state.current_stage if has_approval and approval_state is not None else None,
        blocking_count=precheck_state.blocking_count if has_precheck and precheck_state is not None else (validation_vm.summary.blocking_count if validation_vm is not None else 0),
        warning_count=precheck_state.warning_count if has_precheck and precheck_state is not None else (validation_vm.summary.warning_count if validation_vm is not None else 0),
        confirmation_count=precheck_state.confirmation_count if has_precheck and precheck_state is not None else (validation_vm.summary.confirmation_count if validation_vm is not None else 0),
        pending_decision_count=approval_state.unanswered_decision_count if has_approval and approval_state is not None else 0,
        requires_confirmation=preview_state.requires_confirmation if has_preview and preview_state is not None else False,
        commit_eligible=approval_state.commit_eligible if has_approval and approval_state is not None else False,
        next_step_label=next_step_label,
    )

    if storage_role == "commit_snapshot":
        workflow_status = "committed_context"
    elif storage_role == "execution_record":
        workflow_status = "historical_context"
    elif (validation_vm is not None and validation_vm.overall_status == "blocked") or summary.blocking_count > 0:
        workflow_status = "blocked"
    elif summary.commit_eligible and commit_action is not None and commit_action.enabled:
        workflow_status = "commit_ready"
    elif has_approval and approval_state is not None and approval_state.current_stage not in {None, "none", "idle"}:
        workflow_status = "awaiting_approval"
    elif has_preview and preview_state is not None:
        workflow_status = "preview_ready"
    elif has_intent and intent_state is not None:
        workflow_status = "proposal_in_progress"
    elif storage_role == "working_save":
        workflow_status = "review_ready" if review_action is not None and review_action.enabled else "idle"
    else:
        workflow_status = "empty"

    return ProposalCommitWorkflowViewModel(
        workflow_status=workflow_status,
        storage_role=storage_role,
        beginner_mode=beginner_mode,
        visual_editor=visual_editor_vm,
        node_configuration=node_config_vm,
        storage=storage_vm,
        validation=validation_vm,
        designer=designer_vm,
        action_schema=action_schema,
        summary=summary,
        action_state=ProposalCommitActionStateView(
            review_action=review_action,
            commit_action=commit_action,
            approve_action=approve_action,
            request_revision_action=request_revision_action,
            compare_action=compare_action,
        ),
        beginner_confirmation=_beginner_confirmation(source=source_unwrapped, execution_record=execution_record, preview=preview, patch_plan=patch_plan, intent=intent, approve_action=approve_action, request_revision_action=request_revision_action, app_language=app_language),
        hide_internal_governance_by_default=beginner_mode,
        can_review=bool(review_action and review_action.enabled),
        can_commit=bool(commit_action and commit_action.enabled),
        can_compare_to_commit=bool(compare_action and compare_action.enabled),
        explanation=explanation,
    )


__all__ = [
    "ProposalCommitSummaryView",
    "ProposalCommitActionStateView",
    "BeginnerProposalConfirmationView",
    "ProposalCommitWorkflowViewModel",
    "read_proposal_commit_workflow_view_model",
]
