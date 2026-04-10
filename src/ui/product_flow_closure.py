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
from src.ui.product_flow_e2e_path import ProductFlowE2ECheckpointView, ProductFlowE2EPathViewModel, read_product_flow_e2e_path_view_model
from src.ui.product_flow_handoff import ProductFlowHandoffViewModel, read_product_flow_handoff_view_model
from src.ui.product_flow_readiness import ProductFlowBoundaryReadinessView, ProductFlowReadinessViewModel, read_product_flow_readiness_view_model
from src.ui.product_flow_runbook import ProductFlowRunbookEntryView, ProductFlowRunbookViewModel, read_product_flow_runbook_view_model


@dataclass(frozen=True)
class ProductFlowClosureStageView:
    stage_id: str
    label: str
    stage_status: str
    stage_status_label: str
    closed: bool = False
    closeable: bool = False
    required_action_id: str | None = None
    required_action_label: str | None = None
    recommended_flow_id: str | None = None
    workspace_id: str | None = None
    panel_id: str | None = None
    target_ref: str | None = None
    open_requirement: str | None = None
    open_requirement_label: str | None = None


@dataclass(frozen=True)
class ProductFlowClosureViewModel:
    closure_status: str = "empty"
    closure_status_label: str | None = None
    source_role: str = "none"
    current_stage_id: str = "review"
    next_closure_stage_id: str | None = None
    primary_open_requirement_id: str | None = None
    primary_open_requirement_label: str | None = None
    primary_recommended_flow_id: str | None = None
    terminal_closure_ready: bool = False
    closed_stage_count: int = 0
    closeable_stage_count: int = 0
    blocked_stage_count: int = 0
    stages: list[ProductFlowClosureStageView] = field(default_factory=list)
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None
_STAGE_ORDER = ("review", "approval", "commit", "run", "followthrough")
_REQUIRED_ACTION_BY_STAGE = {
    "review": "review_draft",
    "approval": "approve_for_commit",
    "commit": "commit_snapshot",
    "run": "run_current",
    "followthrough": "open_trace",
}
_FLOW_BY_ACTION = {
    "review_draft": "flow:review_draft",
    "approve_for_commit": "flow:approve_for_commit",
    "commit_snapshot": "flow:commit_snapshot",
    "run_current": "flow:run_current",
    "run_from_commit": "flow:run_from_commit",
    "open_latest_run": "flow:open_latest_run",
    "open_trace": "flow:open_trace",
    "open_artifacts": "flow:open_artifacts",
    "compare_runs": "flow:compare_runs",
    "open_diff": "flow:open_diff",
    "replay_latest": "flow:replay_latest",
}
_RUNBOOK_STAGE_IDS = {
    "review": "review_proposal",
    "approval": "approval_decision",
    "commit": "commit_snapshot",
    "run": "run_current",
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


def _readiness_map(readiness: ProductFlowReadinessViewModel | None) -> dict[str, ProductFlowBoundaryReadinessView]:
    if readiness is None:
        return {}
    return {item.boundary_id: item for item in readiness.boundaries}


def _checkpoint_map(e2e_path: ProductFlowE2EPathViewModel | None) -> dict[str, ProductFlowE2ECheckpointView]:
    if e2e_path is None:
        return {}
    return {item.checkpoint_id: item for item in e2e_path.checkpoints}


def _runbook_map(runbook: ProductFlowRunbookViewModel | None) -> dict[str, ProductFlowRunbookEntryView]:
    if runbook is None:
        return {}
    return {item.entry_id: item for item in runbook.entries}


def _stage_label(stage_id: str, *, app_language: str) -> str:
    return ui_text(f"closure.stage.{stage_id}", app_language=app_language, fallback_text=stage_id.replace("_", " ").title())


def _stage_status_label(stage_status: str, *, app_language: str) -> str:
    return ui_text(f"closure.stage_status.{stage_status}", app_language=app_language, fallback_text=stage_status.replace("_", " ").title())


def _action_label(action_id: str | None, *, app_language: str) -> str | None:
    if action_id is None:
        return None
    return ui_text(f"builder.action.{action_id}", app_language=app_language, fallback_text=action_id.replace("_", " ").title())


def _flow_id_for_stage(stage_id: str, *, handoff: ProductFlowHandoffViewModel | None = None, required_action_id: str | None = None) -> str | None:
    if stage_id == "followthrough" and handoff is not None and handoff.followthrough_action_id is not None:
        return _FLOW_BY_ACTION.get(handoff.followthrough_action_id)
    if required_action_id is not None:
        return _FLOW_BY_ACTION.get(required_action_id)
    return _FLOW_BY_ACTION.get(_REQUIRED_ACTION_BY_STAGE.get(stage_id, ""))


def _build_stage_view(
    stage_id: str,
    *,
    readiness_map: dict[str, ProductFlowBoundaryReadinessView],
    checkpoint_map: dict[str, ProductFlowE2ECheckpointView],
    runbook_map: dict[str, ProductFlowRunbookEntryView],
    handoff: ProductFlowHandoffViewModel | None,
    app_language: str,
) -> ProductFlowClosureStageView:
    readiness = readiness_map.get(stage_id if stage_id != "followthrough" else "followthrough")
    checkpoint = checkpoint_map.get(stage_id)
    runbook_entry = runbook_map.get(_RUNBOOK_STAGE_IDS[stage_id]) if stage_id in _RUNBOOK_STAGE_IDS else None

    closed = bool((readiness is not None and readiness.complete) or (checkpoint is not None and checkpoint.complete))
    closeable = bool((readiness is not None and readiness.ready) or (checkpoint is not None and checkpoint.actionable) or (runbook_entry is not None and runbook_entry.enabled))
    blocked_reason = None
    if checkpoint is not None and checkpoint.blocked_reason:
        blocked_reason = checkpoint.blocked_reason
    elif readiness is not None and readiness.open_requirement_label is not None and not readiness.ready and not readiness.complete:
        blocked_reason = readiness.open_requirement_label
    elif runbook_entry is not None and runbook_entry.reason_disabled:
        blocked_reason = runbook_entry.reason_disabled

    if closed:
        stage_status = "closed"
    elif closeable:
        stage_status = "closeable"
    elif blocked_reason is not None:
        stage_status = "blocked"
    else:
        stage_status = "waiting"

    required_action_id = None
    workspace_id = None
    panel_id = None
    target_ref = None
    if checkpoint is not None and checkpoint.action_id is not None:
        required_action_id = checkpoint.action_id
        workspace_id = checkpoint.workspace_id
        panel_id = checkpoint.panel_id
        target_ref = checkpoint.target_ref
    elif runbook_entry is not None and runbook_entry.action_id is not None:
        required_action_id = runbook_entry.action_id
        workspace_id = runbook_entry.preferred_workspace_id
        panel_id = runbook_entry.preferred_panel_id
        target_ref = runbook_entry.target_ref
    elif readiness is not None and readiness.action_id is not None:
        required_action_id = readiness.action_id
        workspace_id = readiness.workspace_id
        panel_id = readiness.panel_id
        target_ref = readiness.target_ref
    elif stage_id == "followthrough" and handoff is not None:
        required_action_id = handoff.followthrough_action_id or _REQUIRED_ACTION_BY_STAGE[stage_id]
        workspace_id = handoff.followthrough_workspace_id
        panel_id = handoff.followthrough_panel_id
        target_ref = handoff.followthrough_target_ref
    else:
        required_action_id = _REQUIRED_ACTION_BY_STAGE.get(stage_id)
        if readiness is not None:
            workspace_id = readiness.workspace_id
            panel_id = readiness.panel_id
            target_ref = readiness.target_ref

    open_requirement = None if closed else (required_action_id or (readiness.open_requirement if readiness is not None else None) or _REQUIRED_ACTION_BY_STAGE.get(stage_id))
    return ProductFlowClosureStageView(
        stage_id=stage_id,
        label=_stage_label(stage_id, app_language=app_language),
        stage_status=stage_status,
        stage_status_label=_stage_status_label(stage_status, app_language=app_language),
        closed=closed,
        closeable=closeable,
        required_action_id=required_action_id,
        required_action_label=_action_label(required_action_id, app_language=app_language),
        recommended_flow_id=_flow_id_for_stage(stage_id, handoff=handoff, required_action_id=required_action_id),
        workspace_id=workspace_id,
        panel_id=panel_id,
        target_ref=target_ref,
        open_requirement=open_requirement if not closeable and not closed else None,
        open_requirement_label=(_action_label(open_requirement, app_language=app_language) if open_requirement is not None and not closeable and not closed else None),
    )


def read_product_flow_closure_view_model(
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
    runbook: ProductFlowRunbookViewModel | None = None,
    handoff: ProductFlowHandoffViewModel | None = None,
    readiness: ProductFlowReadinessViewModel | None = None,
    e2e_path: ProductFlowE2EPathViewModel | None = None,
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None,
    explanation: str | None = None,
) -> ProductFlowClosureViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    if source_unwrapped is None and execution_record is None:
        return ProductFlowClosureViewModel()

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
        runbook=runbook,
    )
    end_user_flow_hub = end_user_flow_hub or read_builder_end_user_flow_hub_view_model(base_source)
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
        runbook=runbook,
        handoff=handoff,
        end_user_flow_hub=end_user_flow_hub,
    )
    e2e_path = e2e_path or read_product_flow_e2e_path_view_model(
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
        runbook=runbook,
        handoff=handoff,
        readiness=readiness,
        end_user_flow_hub=end_user_flow_hub,
    )

    readiness_map = _readiness_map(readiness)
    checkpoint_map = _checkpoint_map(e2e_path)
    runbook_map = _runbook_map(runbook)
    stages = [
        _build_stage_view(
            stage_id,
            readiness_map=readiness_map,
            checkpoint_map=checkpoint_map,
            runbook_map=runbook_map,
            handoff=handoff,
            app_language=app_language,
        )
        for stage_id in _STAGE_ORDER
    ]

    closed_stage_count = sum(1 for stage in stages if stage.closed)
    closeable_stage_count = sum(1 for stage in stages if stage.closeable)
    blocked_stage_count = sum(1 for stage in stages if stage.stage_status == "blocked")

    current_stage_id = e2e_path.current_checkpoint_id if e2e_path is not None else next((stage.stage_id for stage in stages if not stage.closed), "review")
    next_closure_stage_id = next((stage.stage_id for stage in stages if not stage.closed and stage.stage_id != current_stage_id), None)
    primary_stage = next((stage for stage in stages if not stage.closed), None)

    terminal_closure_ready = bool(
        (readiness is not None and readiness.terminal_ready)
        or (end_user_flow_hub is not None and end_user_flow_hub.lifecycle_closure is not None and end_user_flow_hub.lifecycle_closure.terminal_completion_ready)
        or all(stage.closed for stage in stages)
    )

    if not stages:
        closure_status = "empty"
    elif terminal_closure_ready:
        closure_status = "terminal"
    elif closeable_stage_count:
        closure_status = "actionable"
    elif blocked_stage_count:
        closure_status = "blocked"
    else:
        closure_status = "ready"

    primary_open_requirement_id = None if primary_stage is None else (primary_stage.required_action_id or primary_stage.open_requirement)
    return ProductFlowClosureViewModel(
        closure_status=closure_status,
        closure_status_label=ui_text(f"closure.status.{closure_status}", app_language=app_language, fallback_text=closure_status.replace("_", " ").title()),
        source_role=source_role,
        current_stage_id=current_stage_id,
        next_closure_stage_id=next_closure_stage_id,
        primary_open_requirement_id=primary_open_requirement_id,
        primary_open_requirement_label=_action_label(primary_open_requirement_id, app_language=app_language),
        primary_recommended_flow_id=(primary_stage.recommended_flow_id if primary_stage is not None else None),
        terminal_closure_ready=terminal_closure_ready,
        closed_stage_count=closed_stage_count,
        closeable_stage_count=closeable_stage_count,
        blocked_stage_count=blocked_stage_count,
        stages=stages,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowClosureStageView",
    "ProductFlowClosureViewModel",
    "read_product_flow_closure_view_model",
]
