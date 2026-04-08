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
from src.ui.product_flow_runbook import ProductFlowRunbookEntryView, ProductFlowRunbookViewModel, read_product_flow_runbook_view_model


@dataclass(frozen=True)
class ProductFlowBoundaryReadinessView:
    boundary_id: str
    label: str
    boundary_status: str
    boundary_status_label: str
    ready: bool = False
    complete: bool = False
    action_id: str | None = None
    workspace_id: str | None = None
    panel_id: str | None = None
    target_ref: str | None = None
    open_requirement: str | None = None
    open_requirement_label: str | None = None


@dataclass(frozen=True)
class ProductFlowReadinessViewModel:
    readiness_status: str = "empty"
    readiness_status_label: str | None = None
    source_role: str = "none"
    current_boundary_id: str = "review"
    primary_requirement_action_id: str | None = None
    primary_requirement_label: str | None = None
    ready_boundary_count: int = 0
    complete_boundary_count: int = 0
    blocked_boundary_count: int = 0
    open_requirement_count: int = 0
    terminal_ready: bool = False
    boundaries: list[ProductFlowBoundaryReadinessView] = field(default_factory=list)
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None
_BOUNDARY_ORDER = ("review", "approval", "commit", "run", "followthrough")


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


def _entry_map(runbook: ProductFlowRunbookViewModel | None) -> dict[str, ProductFlowRunbookEntryView]:
    if runbook is None:
        return {}
    return {entry.entry_id: entry for entry in runbook.entries}


def _boundary_status_from_entry(entry: ProductFlowRunbookEntryView | None) -> str:
    if entry is None:
        return "waiting"
    if entry.complete:
        return "complete"
    if entry.enabled:
        return "ready"
    if entry.reason_disabled:
        return "blocked"
    return entry.entry_status or "waiting"


def _boundary_view_from_entry(boundary_id: str, label: str, entry: ProductFlowRunbookEntryView | None, *, app_language: str) -> ProductFlowBoundaryReadinessView:
    status = _boundary_status_from_entry(entry)
    action_id = entry.action_id if entry is not None and entry.enabled else None
    open_requirement = None if entry is None or entry.complete or entry.enabled else (entry.action_id or entry.entry_id)
    return ProductFlowBoundaryReadinessView(
        boundary_id=boundary_id,
        label=label,
        boundary_status=status,
        boundary_status_label=ui_text(f"readiness.status.{status}", app_language=app_language, fallback_text=status.replace("_", " ")),
        ready=bool(entry is not None and entry.enabled),
        complete=bool(entry is not None and entry.complete),
        action_id=action_id,
        workspace_id=(entry.preferred_workspace_id if entry is not None else None),
        panel_id=(entry.preferred_panel_id if entry is not None else None),
        target_ref=(entry.target_ref if entry is not None else None),
        open_requirement=open_requirement,
        open_requirement_label=(ui_text(f"builder.action.{open_requirement}", app_language=app_language, fallback_text=open_requirement.replace("_", " ").title()) if open_requirement is not None else None),
    )


def _followthrough_boundary(runbook: ProductFlowRunbookViewModel | None, handoff: ProductFlowHandoffViewModel | None, *, app_language: str) -> ProductFlowBoundaryReadinessView:
    entries = _entry_map(runbook)
    follow_entries = [entries.get("inspect_trace"), entries.get("inspect_artifacts"), entries.get("compare_results")]
    complete = any(entry is not None and entry.complete for entry in follow_entries)
    ready = any(entry is not None and entry.enabled for entry in follow_entries) or bool(handoff is not None and handoff.followthrough_available)
    blocked = (not ready) and all(entry is not None and entry.reason_disabled for entry in follow_entries if entry is not None) and any(entry is not None for entry in follow_entries)
    if complete:
        status = "complete"
    elif ready:
        status = "ready"
    elif blocked:
        status = "blocked"
    else:
        status = "waiting"

    preferred = None
    if handoff is not None and handoff.followthrough_entry_id is not None:
        preferred = entries.get(handoff.followthrough_entry_id)
    if preferred is None:
        preferred = next((entry for entry in follow_entries if entry is not None and (entry.enabled or entry.complete)), None)
    open_requirement = None if complete or ready else "run_current"
    return ProductFlowBoundaryReadinessView(
        boundary_id="followthrough",
        label=ui_text("readiness.boundary.followthrough", app_language=app_language, fallback_text="Follow-through"),
        boundary_status=status,
        boundary_status_label=ui_text(f"readiness.status.{status}", app_language=app_language, fallback_text=status.replace("_", " ")),
        ready=ready,
        complete=complete,
        action_id=(preferred.action_id if preferred is not None and preferred.enabled else None),
        workspace_id=(preferred.preferred_workspace_id if preferred is not None else handoff.followthrough_workspace_id if handoff is not None else None),
        panel_id=(preferred.preferred_panel_id if preferred is not None else handoff.followthrough_panel_id if handoff is not None else None),
        target_ref=(preferred.target_ref if preferred is not None else handoff.followthrough_target_ref if handoff is not None else None),
        open_requirement=open_requirement,
        open_requirement_label=(ui_text("builder.action.run_current", app_language=app_language, fallback_text="Run Current") if open_requirement is not None else None),
    )


def _current_boundary(boundaries: list[ProductFlowBoundaryReadinessView], *, source_role: str, handoff: ProductFlowHandoffViewModel | None = None, execution_record: ExecutionRecordModel | None = None) -> str:
    if source_role == "working_save" and handoff is not None and handoff.primary_entry_id is not None:
        mapping = {
            "review_proposal": "review",
            "approval_decision": "approval",
            "commit_snapshot": "commit",
            "run_current": "run",
            "inspect_trace": "followthrough",
            "inspect_artifacts": "followthrough",
            "compare_results": "followthrough",
        }
        preferred = mapping.get(handoff.primary_entry_id)
        if preferred is not None:
            return preferred
    if source_role == "execution_record":
        for boundary_id in ("followthrough", "run"):
            for boundary in boundaries:
                if boundary.boundary_id == boundary_id and (boundary.ready or boundary.complete):
                    return boundary.boundary_id
    for boundary in boundaries:
        if not boundary.complete:
            return boundary.boundary_id
    return boundaries[-1].boundary_id if boundaries else "review"


def read_product_flow_readiness_view_model(
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
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None,
    explanation: str | None = None,
) -> ProductFlowReadinessViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    workflow_hub = workflow_hub or read_builder_workflow_hub_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    journey = journey or read_product_flow_journey_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    runbook = runbook or read_product_flow_runbook_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
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
    ) if (source_unwrapped is not None or execution_record is not None) else None

    handoff = handoff or read_product_flow_handoff_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
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
    ) if (source_unwrapped is not None or execution_record is not None) else None

    end_user_flow_hub = end_user_flow_hub or read_builder_end_user_flow_hub_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    entries = _entry_map(runbook)
    boundaries = [
        _boundary_view_from_entry("review", ui_text("readiness.boundary.review", app_language=app_language, fallback_text="Review"), entries.get("review_proposal"), app_language=app_language),
        _boundary_view_from_entry("approval", ui_text("readiness.boundary.approval", app_language=app_language, fallback_text="Approval"), entries.get("approval_decision"), app_language=app_language),
        _boundary_view_from_entry("commit", ui_text("readiness.boundary.commit", app_language=app_language, fallback_text="Commit"), entries.get("commit_snapshot"), app_language=app_language),
        _boundary_view_from_entry("run", ui_text("readiness.boundary.run", app_language=app_language, fallback_text="Run"), entries.get("run_current"), app_language=app_language),
        _followthrough_boundary(runbook, handoff, app_language=app_language),
    ]

    current_boundary_id = _current_boundary(boundaries, source_role=source_role, handoff=handoff, execution_record=execution_record)
    current_boundary = next((boundary for boundary in boundaries if boundary.boundary_id == current_boundary_id), None)
    ready_boundary_count = sum(1 for boundary in boundaries if boundary.ready)
    complete_boundary_count = sum(1 for boundary in boundaries if boundary.complete)
    blocked_boundary_count = sum(1 for boundary in boundaries if boundary.boundary_status == "blocked")
    open_requirement_count = sum(1 for boundary in boundaries if boundary.open_requirement is not None)
    terminal_ready = bool(boundaries and boundaries[-1].complete and (source_role == "execution_record" or (end_user_flow_hub is not None and end_user_flow_hub.lifecycle_closure is not None and end_user_flow_hub.lifecycle_closure.terminal_completion_ready and source_role == "execution_record")))

    if not boundaries:
        readiness_status = "empty"
    elif blocked_boundary_count and any(boundary.boundary_id != "followthrough" for boundary in boundaries if boundary.boundary_status == "blocked"):
        readiness_status = "blocked"
    elif terminal_ready:
        readiness_status = "terminal"
    elif open_requirement_count:
        readiness_status = "attention"
    else:
        readiness_status = "ready"

    return ProductFlowReadinessViewModel(
        readiness_status=readiness_status,
        readiness_status_label=ui_text(f"readiness.status.{readiness_status}", app_language=app_language, fallback_text=readiness_status.replace("_", " ")),
        source_role=source_role,
        current_boundary_id=current_boundary_id,
        primary_requirement_action_id=(current_boundary.open_requirement if current_boundary is not None else None),
        primary_requirement_label=(current_boundary.open_requirement_label if current_boundary is not None else None),
        ready_boundary_count=ready_boundary_count,
        complete_boundary_count=complete_boundary_count,
        blocked_boundary_count=blocked_boundary_count,
        open_requirement_count=open_requirement_count,
        terminal_ready=terminal_ready,
        boundaries=boundaries,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowBoundaryReadinessView",
    "ProductFlowReadinessViewModel",
    "read_product_flow_readiness_view_model",
]
