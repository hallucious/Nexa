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
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.product_flow_handoff import ProductFlowHandoffViewModel, read_product_flow_handoff_view_model
from src.ui.product_flow_journey import ProductFlowJourneyViewModel, read_product_flow_journey_view_model
from src.ui.product_flow_readiness import ProductFlowReadinessViewModel, read_product_flow_readiness_view_model
from src.ui.product_flow_runbook import ProductFlowRunbookEntryView, ProductFlowRunbookViewModel, read_product_flow_runbook_view_model


@dataclass(frozen=True)
class ProductFlowE2ECheckpointView:
    checkpoint_id: str
    label: str
    checkpoint_status: str
    checkpoint_status_label: str
    action_id: str | None = None
    workspace_id: str | None = None
    panel_id: str | None = None
    target_ref: str | None = None
    complete: bool = False
    actionable: bool = False
    blocked_reason: str | None = None


@dataclass(frozen=True)
class ProductFlowE2EPathViewModel:
    path_status: str = "empty"
    path_status_label: str | None = None
    source_role: str = "none"
    current_checkpoint_id: str = "review"
    recommended_checkpoint_id: str | None = None
    next_action_id: str | None = None
    next_action_label: str | None = None
    next_workspace_id: str | None = None
    next_panel_id: str | None = None
    completed_checkpoint_count: int = 0
    actionable_checkpoint_count: int = 0
    blocked_checkpoint_count: int = 0
    terminal_ready: bool = False
    checkpoints: list[ProductFlowE2ECheckpointView] = field(default_factory=list)
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None

_CHECKPOINT_ORDER = (
    "review",
    "approval",
    "commit",
    "run",
    "trace",
    "artifact",
    "diff",
)

_ENTRY_TO_CHECKPOINT = {
    "review_proposal": "review",
    "approval_decision": "approval",
    "commit_snapshot": "commit",
    "run_current": "run",
    "inspect_trace": "trace",
    "inspect_artifacts": "artifact",
    "compare_results": "diff",
}


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


def _runbook_entry_map(runbook: ProductFlowRunbookViewModel | None) -> dict[str, ProductFlowRunbookEntryView]:
    if runbook is None:
        return {}
    return {entry.entry_id: entry for entry in runbook.entries}


def _checkpoint_label(checkpoint_id: str, *, app_language: str) -> str:
    fallback = checkpoint_id.replace("_", " ").title()
    return ui_text(f"e2e.checkpoint.{checkpoint_id}", app_language=app_language, fallback_text=fallback)


def _checkpoint_from_entry(checkpoint_id: str, entry: ProductFlowRunbookEntryView | None, *, app_language: str) -> ProductFlowE2ECheckpointView:
    if entry is None:
        status = "waiting"
        return ProductFlowE2ECheckpointView(
            checkpoint_id=checkpoint_id,
            label=_checkpoint_label(checkpoint_id, app_language=app_language),
            checkpoint_status=status,
            checkpoint_status_label=ui_text(f"runbook.entry_status.{status}", app_language=app_language, fallback_text=status.title()),
        )

    return ProductFlowE2ECheckpointView(
        checkpoint_id=checkpoint_id,
        label=_checkpoint_label(checkpoint_id, app_language=app_language),
        checkpoint_status=entry.entry_status,
        checkpoint_status_label=ui_text(f"runbook.entry_status.{entry.entry_status}", app_language=app_language, fallback_text=entry.entry_status.title()),
        action_id=entry.action_id if entry.enabled else None,
        workspace_id=entry.preferred_workspace_id,
        panel_id=entry.preferred_panel_id,
        target_ref=entry.target_ref,
        complete=entry.complete,
        actionable=entry.enabled,
        blocked_reason=entry.reason_disabled,
    )


def _current_checkpoint(
    checkpoints: list[ProductFlowE2ECheckpointView],
    *,
    source_role: str,
    handoff: ProductFlowHandoffViewModel | None,
) -> str:
    if source_role == "working_save" and handoff is not None and handoff.primary_entry_id is not None:
        preferred = _ENTRY_TO_CHECKPOINT.get(handoff.primary_entry_id)
        if preferred is not None:
            return preferred
    if source_role == "execution_record":
        for checkpoint_id in ("trace", "artifact", "diff", "run"):
            checkpoint = next((item for item in checkpoints if item.checkpoint_id == checkpoint_id), None)
            if checkpoint is not None and (checkpoint.actionable or checkpoint.complete):
                return checkpoint_id
    for checkpoint in checkpoints:
        if not checkpoint.complete:
            return checkpoint.checkpoint_id
    return checkpoints[-1].checkpoint_id if checkpoints else "review"


def _recommended_checkpoint_id(
    checkpoints: list[ProductFlowE2ECheckpointView],
    *,
    source_role: str,
    handoff: ProductFlowHandoffViewModel | None,
) -> str | None:
    if handoff is not None:
        if source_role == "execution_record" and handoff.followthrough_entry_id is not None:
            preferred = _ENTRY_TO_CHECKPOINT.get(handoff.followthrough_entry_id)
            if preferred is not None:
                return preferred
        if handoff.primary_entry_id is not None:
            preferred = _ENTRY_TO_CHECKPOINT.get(handoff.primary_entry_id)
            if preferred is not None:
                return preferred
    for checkpoint in checkpoints:
        if checkpoint.actionable:
            return checkpoint.checkpoint_id
    for checkpoint in checkpoints:
        if not checkpoint.complete:
            return checkpoint.checkpoint_id
    return checkpoints[-1].checkpoint_id if checkpoints else None


def _terminal_ready(
    checkpoints: list[ProductFlowE2ECheckpointView],
    *,
    readiness: ProductFlowReadinessViewModel | None,
) -> bool:
    if readiness is not None and readiness.terminal_ready:
        return True
    core_ids = {"review", "approval", "commit", "run"}
    core_complete = all(
        next((item.complete for item in checkpoints if item.checkpoint_id == checkpoint_id), False)
        for checkpoint_id in core_ids
    )
    followthrough_closed = any(
        item.checkpoint_id in {"trace", "artifact", "diff"} and (item.complete or item.actionable)
        for item in checkpoints
    )
    return core_complete and followthrough_closed


def read_product_flow_e2e_path_view_model(
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
    workflow_hub: BuilderWorkflowHubViewModel | None = None,
    journey: ProductFlowJourneyViewModel | None = None,
    runbook: ProductFlowRunbookViewModel | None = None,
    handoff: ProductFlowHandoffViewModel | None = None,
    readiness: ProductFlowReadinessViewModel | None = None,
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None,
    explanation: str | None = None,
) -> ProductFlowE2EPathViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    if source_unwrapped is None and execution_record is None:
        return ProductFlowE2EPathViewModel()

    base_source = source_unwrapped if source_unwrapped is not None else execution_record

    workflow_hub = workflow_hub or read_builder_workflow_hub_view_model(
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
    journey = journey or read_product_flow_journey_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        prefer_active_workflow_focus=True,
    )
    runbook = runbook or read_product_flow_runbook_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey,
    )
    handoff = handoff or read_product_flow_handoff_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey,
        runbook=runbook,
    )
    readiness = readiness or read_product_flow_readiness_view_model(
        base_source,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey,
        runbook=runbook,
        handoff=handoff,
        end_user_flow_hub=end_user_flow_hub,
    )
    end_user_flow_hub = end_user_flow_hub or read_builder_end_user_flow_hub_view_model(base_source)

    entries = _runbook_entry_map(runbook)
    checkpoints = [
        _checkpoint_from_entry("review", entries.get("review_proposal"), app_language=app_language),
        _checkpoint_from_entry("approval", entries.get("approval_decision"), app_language=app_language),
        _checkpoint_from_entry("commit", entries.get("commit_snapshot"), app_language=app_language),
        _checkpoint_from_entry("run", entries.get("run_current"), app_language=app_language),
        _checkpoint_from_entry("trace", entries.get("inspect_trace"), app_language=app_language),
        _checkpoint_from_entry("artifact", entries.get("inspect_artifacts"), app_language=app_language),
        _checkpoint_from_entry("diff", entries.get("compare_results"), app_language=app_language),
    ]

    current_checkpoint_id = _current_checkpoint(checkpoints, source_role=source_role, handoff=handoff)
    recommended_checkpoint_id = _recommended_checkpoint_id(checkpoints, source_role=source_role, handoff=handoff)
    recommended_checkpoint = next((item for item in checkpoints if item.checkpoint_id == recommended_checkpoint_id), None)

    completed_checkpoint_count = sum(1 for item in checkpoints if item.complete)
    actionable_checkpoint_count = sum(1 for item in checkpoints if item.actionable)
    blocked_checkpoint_count = sum(1 for item in checkpoints if item.checkpoint_status == "blocked")
    terminal_ready = _terminal_ready(checkpoints, readiness=readiness)

    non_followthrough_blocked = any(
        item.checkpoint_id in {"review", "approval", "commit", "run"} and item.checkpoint_status == "blocked"
        for item in checkpoints
    )
    followthrough_available = any(
        item.checkpoint_id in {"trace", "artifact", "diff"} and (item.actionable or item.complete)
        for item in checkpoints
    )

    if not checkpoints:
        path_status = "empty"
    elif non_followthrough_blocked and (recommended_checkpoint is None or not recommended_checkpoint.actionable):
        path_status = "blocked"
    elif source_role == "execution_record" and followthrough_available:
        path_status = "followthrough"
    elif terminal_ready:
        path_status = "terminal"
    elif recommended_checkpoint is not None and recommended_checkpoint.actionable:
        path_status = "actionable"
    elif blocked_checkpoint_count:
        path_status = "attention"
    else:
        path_status = "ready"

    next_action_id = recommended_checkpoint.action_id if recommended_checkpoint is not None and recommended_checkpoint.actionable else handoff.primary_action_id if handoff is not None else None
    next_action_label = (
        ui_text(f"builder.action.{next_action_id}", app_language=app_language, fallback_text=next_action_id.replace("_", " ").title())
        if next_action_id is not None
        else None
    )

    return ProductFlowE2EPathViewModel(
        path_status=path_status,
        path_status_label=ui_text(f"e2e.status.{path_status}", app_language=app_language, fallback_text=path_status.replace("_", " ")),
        source_role=source_role,
        current_checkpoint_id=current_checkpoint_id,
        recommended_checkpoint_id=recommended_checkpoint_id,
        next_action_id=next_action_id,
        next_action_label=next_action_label,
        next_workspace_id=(recommended_checkpoint.workspace_id if recommended_checkpoint is not None else handoff.primary_workspace_id if handoff is not None else None),
        next_panel_id=(recommended_checkpoint.panel_id if recommended_checkpoint is not None else handoff.primary_panel_id if handoff is not None else None),
        completed_checkpoint_count=completed_checkpoint_count,
        actionable_checkpoint_count=actionable_checkpoint_count,
        blocked_checkpoint_count=blocked_checkpoint_count,
        terminal_ready=terminal_ready,
        checkpoints=checkpoints,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowE2ECheckpointView",
    "ProductFlowE2EPathViewModel",
    "read_product_flow_e2e_path_view_model",
]
