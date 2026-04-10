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
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.product_flow_journey import ProductFlowJourneyViewModel, read_product_flow_journey_view_model
from src.ui.product_flow_runbook import ProductFlowRunbookEntryView, ProductFlowRunbookViewModel, read_product_flow_runbook_view_model


@dataclass(frozen=True)
class ProductFlowHandoffViewModel:
    handoff_status: str = "empty"
    handoff_status_label: str | None = None
    source_role: str = "none"
    current_handoff_id: str = "empty"
    primary_entry_id: str | None = None
    primary_entry_label: str | None = None
    primary_action_id: str | None = None
    primary_workspace_id: str | None = None
    primary_panel_id: str | None = None
    primary_target_ref: str | None = None
    primary_enabled: bool = False
    primary_complete: bool = False
    primary_requires_confirmation: bool = False
    followthrough_entry_id: str | None = None
    followthrough_entry_label: str | None = None
    followthrough_action_id: str | None = None
    followthrough_workspace_id: str | None = None
    followthrough_panel_id: str | None = None
    followthrough_target_ref: str | None = None
    followthrough_available: bool = False
    blocked_reason: str | None = None
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None

_ENTRY_ORDER = (
    "review_proposal",
    "approval_decision",
    "commit_snapshot",
    "run_current",
    "inspect_trace",
    "inspect_artifacts",
    "compare_results",
)


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


def _ordered_entries(runbook: ProductFlowRunbookViewModel | None) -> list[ProductFlowRunbookEntryView]:
    if runbook is None:
        return []
    entries = _entry_map(runbook)
    return [entries[entry_id] for entry_id in _ENTRY_ORDER if entry_id in entries]


def _choose_primary(runbook: ProductFlowRunbookViewModel | None) -> ProductFlowRunbookEntryView | None:
    if runbook is None:
        return None
    entries = _entry_map(runbook)
    recommended = entries.get(runbook.recommended_entry_id)
    if recommended is not None:
        return recommended
    current = entries.get(runbook.current_entry_id)
    if current is not None:
        return current
    ordered = _ordered_entries(runbook)
    return ordered[0] if ordered else None


def _choose_followthrough(runbook: ProductFlowRunbookViewModel | None, primary: ProductFlowRunbookEntryView | None) -> ProductFlowRunbookEntryView | None:
    if runbook is None or primary is None:
        return None
    ordered = _ordered_entries(runbook)
    try:
        start_index = next(index for index, item in enumerate(ordered) if item.entry_id == primary.entry_id)
    except StopIteration:
        return None

    if primary.entry_id == "run_current":
        preferred_ids = ("inspect_trace", "inspect_artifacts", "compare_results")
        entries = _entry_map(runbook)
        for entry_id in preferred_ids:
            candidate = entries.get(entry_id)
            if candidate is not None and (candidate.enabled or candidate.complete):
                return candidate

    for candidate in ordered[start_index + 1 :]:
        if candidate.enabled or candidate.complete:
            return candidate
    return None




def _prioritized_primary(runbook: ProductFlowRunbookViewModel | None, *, source_role: str) -> ProductFlowRunbookEntryView | None:
    entries = _entry_map(runbook)
    if source_role == "working_save":
        priority = ("commit_snapshot", "approval_decision", "review_proposal", "run_current")
    elif source_role == "commit_snapshot":
        priority = ("run_current", "inspect_trace", "inspect_artifacts", "compare_results", "commit_snapshot")
    elif source_role == "execution_record":
        priority = ("inspect_trace", "inspect_artifacts", "compare_results", "run_current")
    else:
        priority = ()
    for entry_id in priority:
        candidate = entries.get(entry_id)
        if candidate is not None and (candidate.enabled or candidate.complete):
            return candidate
    return _choose_primary(runbook)

def read_product_flow_handoff_view_model(
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
    explanation: str | None = None,
) -> ProductFlowHandoffViewModel:
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

    primary = _prioritized_primary(runbook, source_role=source_role)
    followthrough = _choose_followthrough(runbook, primary)

    if primary is None:
        handoff_status = "empty"
    elif primary.complete and followthrough is not None and (followthrough.enabled or followthrough.complete):
        handoff_status = "followthrough"
    elif primary.enabled and primary.requires_confirmation:
        handoff_status = "confirmation_required"
    elif primary.enabled:
        handoff_status = "ready"
    elif primary.reason_disabled is not None:
        handoff_status = "blocked"
    elif runbook is not None and runbook.runbook_status == "complete":
        handoff_status = "complete"
    else:
        handoff_status = "empty"

    if primary is None:
        current_handoff_id = "empty"
    elif followthrough is None:
        current_handoff_id = f"{primary.entry_id}__to__done"
    else:
        current_handoff_id = f"{primary.entry_id}__to__{followthrough.entry_id}"

    return ProductFlowHandoffViewModel(
        handoff_status=handoff_status,
        handoff_status_label=ui_text(f"handoff.status.{handoff_status}", app_language=app_language, fallback_text=handoff_status.replace("_", " ")),
        source_role=source_role,
        current_handoff_id=current_handoff_id,
        primary_entry_id=(primary.entry_id if primary is not None else None),
        primary_entry_label=(primary.label if primary is not None else None),
        primary_action_id=(primary.action_id if primary is not None else None),
        primary_workspace_id=(primary.preferred_workspace_id if primary is not None else None),
        primary_panel_id=(primary.preferred_panel_id if primary is not None else None),
        primary_target_ref=(primary.target_ref if primary is not None else None),
        primary_enabled=bool(primary is not None and primary.enabled),
        primary_complete=bool(primary is not None and primary.complete),
        primary_requires_confirmation=bool(primary is not None and primary.requires_confirmation),
        followthrough_entry_id=(followthrough.entry_id if followthrough is not None else None),
        followthrough_entry_label=(followthrough.label if followthrough is not None else None),
        followthrough_action_id=(followthrough.action_id if followthrough is not None else None),
        followthrough_workspace_id=(followthrough.preferred_workspace_id if followthrough is not None else None),
        followthrough_panel_id=(followthrough.preferred_panel_id if followthrough is not None else None),
        followthrough_target_ref=(followthrough.target_ref if followthrough is not None else None),
        followthrough_available=bool(followthrough is not None and (followthrough.enabled or followthrough.complete)),
        blocked_reason=(primary.reason_disabled if primary is not None and not primary.enabled else None),
        explanation=explanation,
    )


__all__ = [
    "ProductFlowHandoffViewModel",
    "read_product_flow_handoff_view_model",
]
