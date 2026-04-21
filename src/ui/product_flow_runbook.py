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
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.i18n import beginner_surface_active, ui_language_from_sources, ui_text
from src.ui.product_flow_journey import ProductFlowJourneyViewModel, ProductFlowJourneyStepView, read_product_flow_journey_view_model


@dataclass(frozen=True)
class ProductFlowRunbookEntryView:
    entry_id: str
    label: str
    entry_status: str
    entry_status_label: str
    preferred_workspace_id: str
    preferred_panel_id: str
    action_id: str | None = None
    target_ref: str | None = None
    enabled: bool = False
    complete: bool = False
    requires_confirmation: bool = False
    reason_disabled: str | None = None


@dataclass(frozen=True)
class ProductFlowRunbookViewModel:
    runbook_status: str = "empty"
    runbook_status_label: str | None = None
    source_role: str = "none"
    current_entry_id: str = "review_proposal"
    recommended_entry_id: str = "review_proposal"
    enabled_entry_count: int = 0
    completed_entry_count: int = 0
    blocked_entry_count: int = 0
    entries: list[ProductFlowRunbookEntryView] = field(default_factory=list)
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


def _status_label(status: str, *, app_language: str) -> str:
    return ui_text(f"runbook.entry_status.{status}", app_language=app_language, fallback_text=status.replace("_", " ").title())


def _find_step(journey: ProductFlowJourneyViewModel | None, step_id: str) -> ProductFlowJourneyStepView | None:
    if journey is None:
        return None
    return next((step for step in journey.steps if step.step_id == step_id), None)


def _find_action(action_state, *names: str):
    if action_state is None:
        return None
    for name in names:
        action = getattr(action_state, name, None)
        if action is not None:
            return action
    return None


def _entry_status_from_step(step: ProductFlowJourneyStepView | None, *, fallback: str = "waiting") -> str:
    if step is None:
        return fallback
    return step.step_status


def _has_trace(workflow_hub: BuilderWorkflowHubViewModel | None) -> bool:
    monitoring = workflow_hub.execution_launch.runtime_monitoring if workflow_hub and workflow_hub.execution_launch else None
    return bool(monitoring and monitoring.trace_timeline and monitoring.trace_timeline.events)


def _has_artifacts(workflow_hub: BuilderWorkflowHubViewModel | None) -> bool:
    monitoring = workflow_hub.execution_launch.runtime_monitoring if workflow_hub and workflow_hub.execution_launch else None
    return bool(monitoring and monitoring.artifact and monitoring.artifact.artifact_list)


def _has_diff(workflow_hub: BuilderWorkflowHubViewModel | None) -> bool:
    shell = workflow_hub.shell if workflow_hub is not None else None
    return bool(shell and shell.diff and shell.diff.summary.total_change_count > 0)


def _trace_target_ref(workflow_hub: BuilderWorkflowHubViewModel | None) -> str | None:
    monitoring = workflow_hub.execution_launch.runtime_monitoring if workflow_hub and workflow_hub.execution_launch else None
    if monitoring and monitoring.trace_timeline and monitoring.trace_timeline.run_identity.run_id is not None:
        return f"trace:{monitoring.trace_timeline.run_identity.run_id}"
    return None


def _artifact_target_ref(workflow_hub: BuilderWorkflowHubViewModel | None) -> str | None:
    monitoring = workflow_hub.execution_launch.runtime_monitoring if workflow_hub and workflow_hub.execution_launch else None
    if monitoring and monitoring.artifact and monitoring.artifact.selected_artifact is not None:
        return f"artifact:{monitoring.artifact.selected_artifact.artifact_id}"
    if monitoring and monitoring.artifact and monitoring.artifact.artifact_list:
        return f"artifact:{monitoring.artifact.artifact_list[0].artifact_id}"
    return None


def _diff_target_ref(workflow_hub: BuilderWorkflowHubViewModel | None) -> str | None:
    shell = workflow_hub.shell if workflow_hub is not None else None
    if shell and shell.diff and shell.diff.summary.total_change_count > 0:
        return f"diff:{shell.diff.diff_mode}"
    return None


def _recommended_followthrough_entry(*, workflow_hub: BuilderWorkflowHubViewModel | None, beginner_surface: bool = False) -> str:
    if beginner_surface:
        return "run_current"
    if _has_trace(workflow_hub):
        return "inspect_trace"
    if _has_artifacts(workflow_hub):
        return "inspect_artifacts"
    return "compare_results"


def read_product_flow_runbook_view_model(
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
    explanation: str | None = None,
) -> ProductFlowRunbookViewModel:
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

    proposal_commit = workflow_hub.proposal_commit if workflow_hub is not None else None
    execution_launch = workflow_hub.execution_launch if workflow_hub is not None else None
    beginner_surface = beginner_surface_active(source_unwrapped, execution_record)

    review_step = _find_step(journey, "preview_review")
    approval_step = _find_step(journey, "approval")
    commit_step = _find_step(journey, "commit_snapshot")
    run_step = _find_step(journey, "run_current")
    observe_step = _find_step(journey, "observe_results")

    review_action = _find_action(proposal_commit.action_state if proposal_commit is not None else None, "review_action", "compare_action")
    approve_action = _find_action(proposal_commit.action_state if proposal_commit is not None else None, "approve_action")
    request_revision_action = _find_action(proposal_commit.action_state if proposal_commit is not None else None, "request_revision_action")
    commit_action = _find_action(proposal_commit.action_state if proposal_commit is not None else None, "commit_action")
    run_action = _find_action(execution_launch.action_state if execution_launch is not None else None, "run_action")
    cancel_action = _find_action(execution_launch.action_state if execution_launch is not None else None, "cancel_action")
    replay_action = _find_action(execution_launch.action_state if execution_launch is not None else None, "replay_action")
    compare_action = _find_action(execution_launch.action_state if execution_launch is not None else None, "compare_action")

    inspect_trace_status = "complete" if _has_trace(workflow_hub) and observe_step is not None and observe_step.complete else ("ready" if _has_trace(workflow_hub) else _entry_status_from_step(observe_step))
    inspect_artifact_status = "complete" if _has_artifacts(workflow_hub) and observe_step is not None and observe_step.complete else ("ready" if _has_artifacts(workflow_hub) else _entry_status_from_step(observe_step))
    compare_results_status = "complete" if _has_diff(workflow_hub) and observe_step is not None and observe_step.complete else ("ready" if _has_diff(workflow_hub) else _entry_status_from_step(observe_step))

    entries = [
        ProductFlowRunbookEntryView(
            entry_id="review_proposal",
            label=ui_text("runbook.entry.review_proposal", app_language=app_language, fallback_text="Review proposal"),
            entry_status=_entry_status_from_step(review_step),
            entry_status_label=_status_label(_entry_status_from_step(review_step), app_language=app_language),
            preferred_workspace_id="node_configuration",
            preferred_panel_id="diff" if review_action is not None and review_action.action_id == "open_diff" else "validation",
            action_id=(review_action.action_id if review_action is not None and review_action.enabled else None),
            target_ref=(review_step.target_ref if review_step is not None else None),
            enabled=bool((review_action is not None and review_action.enabled) or (review_step is not None and review_step.complete)),
            complete=bool(review_step is not None and review_step.complete),
            requires_confirmation=bool(review_action is not None and review_action.requires_confirmation),
            reason_disabled=(review_action.reason_disabled if review_action is not None and not review_action.enabled else review_step.blocking_reason if review_step is not None and not review_step.actionable and not review_step.complete else None),
        ),
        ProductFlowRunbookEntryView(
            entry_id="approval_decision",
            label=ui_text("runbook.entry.approval_decision", app_language=app_language, fallback_text="Approve or revise"),
            entry_status=_entry_status_from_step(approval_step),
            entry_status_label=_status_label(_entry_status_from_step(approval_step), app_language=app_language),
            preferred_workspace_id="node_configuration",
            preferred_panel_id="designer",
            action_id=(approve_action.action_id if approve_action is not None and approve_action.enabled else request_revision_action.action_id if request_revision_action is not None and request_revision_action.enabled else None),
            target_ref=(approval_step.target_ref if approval_step is not None else None),
            enabled=bool(
                (approve_action is not None and approve_action.enabled)
                or (request_revision_action is not None and request_revision_action.enabled)
                or (approval_step is not None and approval_step.complete)
            ),
            complete=bool(approval_step is not None and approval_step.complete),
            requires_confirmation=bool(approve_action is not None and approve_action.enabled and approve_action.requires_confirmation),
            reason_disabled=(approve_action.reason_disabled if approve_action is not None and not approve_action.enabled else approval_step.blocking_reason if approval_step is not None and not approval_step.actionable and not approval_step.complete else None),
        ),
        ProductFlowRunbookEntryView(
            entry_id="commit_snapshot",
            label=ui_text("runbook.entry.commit_snapshot", app_language=app_language, fallback_text="Commit snapshot"),
            entry_status=_entry_status_from_step(commit_step),
            entry_status_label=_status_label(_entry_status_from_step(commit_step), app_language=app_language),
            preferred_workspace_id="node_configuration",
            preferred_panel_id="designer",
            action_id=(commit_action.action_id if commit_action is not None and commit_action.enabled else None),
            target_ref=(commit_step.target_ref if commit_step is not None else None),
            enabled=bool((commit_action is not None and commit_action.enabled) or (commit_step is not None and commit_step.complete)),
            complete=bool(commit_step is not None and commit_step.complete),
            requires_confirmation=bool(commit_action is not None and commit_action.requires_confirmation),
            reason_disabled=(commit_action.reason_disabled if commit_action is not None and not commit_action.enabled else commit_step.blocking_reason if commit_step is not None and not commit_step.actionable and not commit_step.complete else None),
        ),
        ProductFlowRunbookEntryView(
            entry_id="run_current",
            label=ui_text("runbook.entry.run_current", app_language=app_language, fallback_text="Launch or monitor run"),
            entry_status=_entry_status_from_step(run_step),
            entry_status_label=_status_label(_entry_status_from_step(run_step), app_language=app_language),
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="execution",
            action_id=(cancel_action.action_id if cancel_action is not None and cancel_action.enabled else run_action.action_id if run_action is not None and run_action.enabled else replay_action.action_id if replay_action is not None and replay_action.enabled and run_step is not None and run_step.complete else None),
            target_ref=(run_step.target_ref if run_step is not None else None),
            enabled=bool(
                (cancel_action is not None and cancel_action.enabled)
                or (run_action is not None and run_action.enabled)
                or (replay_action is not None and replay_action.enabled)
                or (run_step is not None and run_step.complete)
            ),
            complete=bool(run_step is not None and run_step.complete),
            requires_confirmation=bool(cancel_action is not None and cancel_action.enabled and cancel_action.requires_confirmation),
            reason_disabled=(run_action.reason_disabled if run_action is not None and not run_action.enabled and not ((cancel_action is not None and cancel_action.enabled) or (replay_action is not None and replay_action.enabled)) else run_step.blocking_reason if run_step is not None and not run_step.actionable and not run_step.complete else None),
        ),
        ProductFlowRunbookEntryView(
            entry_id="inspect_trace",
            label=ui_text("runbook.entry.inspect_trace", app_language=app_language, fallback_text="Inspect trace"),
            entry_status=inspect_trace_status,
            entry_status_label=_status_label(inspect_trace_status, app_language=app_language),
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="trace_timeline",
            action_id=(None if beginner_surface and source_role == "working_save" else ("open_trace" if _has_trace(workflow_hub) else replay_action.action_id if replay_action is not None and replay_action.enabled and not _has_trace(workflow_hub) else None)),
            target_ref=_trace_target_ref(workflow_hub),
            enabled=bool(False if beginner_surface and source_role == "working_save" else (_has_trace(workflow_hub) or (replay_action is not None and replay_action.enabled))),
            complete=inspect_trace_status == "complete",
            reason_disabled=(observe_step.blocking_reason if not _has_trace(workflow_hub) and not (replay_action is not None and replay_action.enabled) and observe_step is not None else None),
        ),
        ProductFlowRunbookEntryView(
            entry_id="inspect_artifacts",
            label=ui_text("runbook.entry.inspect_artifacts", app_language=app_language, fallback_text="Inspect artifacts"),
            entry_status=inspect_artifact_status,
            entry_status_label=_status_label(inspect_artifact_status, app_language=app_language),
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="artifact",
            action_id=(None if beginner_surface and source_role == "working_save" else ("open_artifacts" if _has_artifacts(workflow_hub) else replay_action.action_id if replay_action is not None and replay_action.enabled and not _has_artifacts(workflow_hub) else None)),
            target_ref=_artifact_target_ref(workflow_hub),
            enabled=False if beginner_surface and source_role == "working_save" else _has_artifacts(workflow_hub),
            complete=inspect_artifact_status == "complete",
            reason_disabled=(observe_step.blocking_reason if not _has_artifacts(workflow_hub) and observe_step is not None else None),
        ),
        ProductFlowRunbookEntryView(
            entry_id="compare_results",
            label=ui_text("runbook.entry.compare_results", app_language=app_language, fallback_text="Compare results"),
            entry_status=compare_results_status,
            entry_status_label=_status_label(compare_results_status, app_language=app_language),
            preferred_workspace_id="runtime_monitoring" if _has_diff(workflow_hub) else "visual_editor",
            preferred_panel_id="diff",
            action_id=(None if beginner_surface and source_role == "working_save" else ((compare_action.action_id if compare_action is not None and compare_action.enabled and compare_action.action_id == "compare_runs" else None) or ("open_diff" if _has_diff(workflow_hub) else None))),
            target_ref=_diff_target_ref(workflow_hub),
            enabled=bool(False if beginner_surface and source_role == "working_save" else (_has_diff(workflow_hub) or (compare_action is not None and compare_action.enabled and compare_action.action_id == "compare_runs"))),
            complete=compare_results_status == "complete",
            reason_disabled=(compare_action.reason_disabled if compare_action is not None and not compare_action.enabled and not _has_diff(workflow_hub) else observe_step.blocking_reason if observe_step is not None and not _has_diff(workflow_hub) else None),
        ),
    ]

    if journey is None:
        current_entry_id = "review_proposal"
    else:
        mapping = {
            "preview_review": "review_proposal",
            "approval": "approval_decision",
            "commit_snapshot": "commit_snapshot",
            "run_current": "run_current",
            "observe_results": _recommended_followthrough_entry(workflow_hub=workflow_hub, beginner_surface=beginner_surface and source_role == "working_save"),
        }
        current_entry_id = mapping.get(journey.current_step_id, "review_proposal")

    entries_by_id = {entry.entry_id: entry for entry in entries}
    if source_role == "commit_snapshot":
        preferred = next((entry_id for entry_id in ("run_current", "inspect_trace", "inspect_artifacts", "compare_results", "commit_snapshot") if entry_id in entries_by_id and (entries_by_id[entry_id].enabled or entries_by_id[entry_id].complete)), None)
        if preferred is not None:
            current_entry_id = preferred
    elif source_role == "execution_record":
        preferred = next((entry_id for entry_id in ("inspect_trace", "inspect_artifacts", "compare_results", "run_current") if entry_id in entries_by_id and (entries_by_id[entry_id].enabled or entries_by_id[entry_id].complete)), None)
        if preferred is not None:
            current_entry_id = preferred

    recommended_entry = next((entry for entry in entries if entry.entry_id == current_entry_id and entry.enabled), None)
    if recommended_entry is None and source_role == "commit_snapshot":
        recommended_entry = next((entries_by_id[entry_id] for entry_id in ("run_current", "inspect_trace", "inspect_artifacts", "compare_results", "commit_snapshot") if entry_id in entries_by_id and entries_by_id[entry_id].enabled), None)
    if recommended_entry is None and source_role == "execution_record":
        recommended_entry = next((entries_by_id[entry_id] for entry_id in ("inspect_trace", "inspect_artifacts", "compare_results", "run_current") if entry_id in entries_by_id and entries_by_id[entry_id].enabled), None)
    if recommended_entry is None:
        recommended_entry = next((entry for entry in entries if entry.entry_status in {"active", "ready"} and entry.enabled), None)
    if recommended_entry is None:
        recommended_entry = next((entry for entry in entries if entry.complete), entries[0] if entries else None)

    enabled_entry_count = sum(1 for entry in entries if entry.enabled)
    completed_entry_count = sum(1 for entry in entries if entry.complete)
    blocked_entry_count = sum(1 for entry in entries if entry.entry_status == "blocked")

    if not entries:
        runbook_status = "empty"
    elif journey is not None and journey.journey_status == "live":
        runbook_status = "live"
    elif source_role == "execution_record":
        runbook_status = "terminal_review"
    elif blocked_entry_count and enabled_entry_count == 0:
        runbook_status = "blocked"
    elif completed_entry_count == len(entries):
        runbook_status = "complete"
    else:
        runbook_status = "ready"

    return ProductFlowRunbookViewModel(
        runbook_status=runbook_status,
        runbook_status_label=ui_text(f"runbook.status.{runbook_status}", app_language=app_language, fallback_text=runbook_status.replace("_", " ")),
        source_role=source_role,
        current_entry_id=current_entry_id,
        recommended_entry_id=(recommended_entry.entry_id if recommended_entry is not None else current_entry_id),
        enabled_entry_count=enabled_entry_count,
        completed_entry_count=completed_entry_count,
        blocked_entry_count=blocked_entry_count,
        entries=entries,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowRunbookEntryView",
    "ProductFlowRunbookViewModel",
    "read_product_flow_runbook_view_model",
]
