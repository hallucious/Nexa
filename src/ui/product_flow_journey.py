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
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class ProductFlowJourneyStepView:
    step_id: str
    step_label: str
    step_status: str
    step_status_label: str
    target_ref: str | None = None
    preferred_workspace_id: str = "visual_editor"
    preferred_panel_id: str = "graph"
    complete: bool = False
    actionable: bool = False
    blocking_reason: str | None = None


@dataclass(frozen=True)
class ProductFlowJourneyViewModel:
    journey_status: str = "empty"
    journey_status_label: str | None = None
    source_role: str = "none"
    current_step_id: str = "designer_request"
    terminal_step_id: str = "observe_results"
    ready_step_count: int = 0
    blocked_step_count: int = 0
    completed_step_count: int = 0
    steps: list[ProductFlowJourneyStepView] = field(default_factory=list)
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
    return ui_text(f"journey.step_status.{status}", app_language=app_language, fallback_text=status.replace("_", " ").title())


def _has_trace_or_artifacts(workflow_hub: BuilderWorkflowHubViewModel | None) -> bool:
    if workflow_hub is None or workflow_hub.execution_launch is None or workflow_hub.execution_launch.runtime_monitoring is None:
        return False
    monitoring = workflow_hub.execution_launch.runtime_monitoring
    shell = workflow_hub.shell
    return bool(
        (monitoring.trace_timeline is not None and monitoring.trace_timeline.events)
        or (monitoring.artifact is not None and monitoring.artifact.artifact_list)
        or (shell is not None and shell.diff is not None and shell.diff.summary.total_change_count > 0)
    )


def read_product_flow_journey_view_model(
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
    prefer_active_workflow_focus: bool = False,
    explanation: str | None = None,
) -> ProductFlowJourneyViewModel:
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

    proposal_commit = workflow_hub.proposal_commit if workflow_hub is not None else None
    execution_launch = workflow_hub.execution_launch if workflow_hub is not None else None

    has_intent = bool(proposal_commit is not None and proposal_commit.summary.current_intent_id)
    has_preview = bool(proposal_commit is not None and proposal_commit.summary.current_preview_id)
    approval_pending = bool(proposal_commit is not None and proposal_commit.summary.pending_decision_count > 0)
    approval_ready = bool(proposal_commit is not None and proposal_commit.summary.current_approval_id)
    commit_complete = bool(
        source_role == "commit_snapshot"
        or (source_role == "execution_record")
        or (execution_record is not None and execution_record.source.commit_id is not None)
        or (execution_launch is not None and execution_launch.summary.commit_anchor_ref is not None)
    )
    run_complete = bool(execution_launch is not None and execution_launch.summary.run_id is not None)
    live_run = bool(execution_launch is not None and execution_launch.summary.execution_status in {"running", "queued"})
    observability_ready = run_complete and _has_trace_or_artifacts(workflow_hub)

    steps: list[ProductFlowJourneyStepView] = []

    designer_status = "complete" if has_intent else ("ready" if source_role == "working_save" else "inactive")
    steps.append(
        ProductFlowJourneyStepView(
            step_id="designer_request",
            step_label=ui_text("journey.step.designer_request", app_language=app_language, fallback_text="Designer request"),
            step_status=designer_status,
            step_status_label=_status_label(designer_status, app_language=app_language),
            target_ref=(proposal_commit.summary.current_intent_id if proposal_commit is not None else None),
            preferred_workspace_id="node_configuration",
            preferred_panel_id="designer",
            complete=designer_status == "complete",
            actionable=designer_status == "ready",
        )
    )

    preview_status = "complete" if has_preview else ("ready" if has_intent else "waiting")
    preview_block = None if preview_status != "waiting" else ui_text("journey.reason.preview_requires_intent", app_language=app_language, fallback_text="Generate an intent before preview")
    steps.append(
        ProductFlowJourneyStepView(
            step_id="preview_review",
            step_label=ui_text("journey.step.preview_review", app_language=app_language, fallback_text="Preview and review"),
            step_status=preview_status,
            step_status_label=_status_label(preview_status, app_language=app_language),
            target_ref=(proposal_commit.summary.current_preview_id if proposal_commit is not None else None),
            preferred_workspace_id="node_configuration",
            preferred_panel_id="diff",
            complete=preview_status == "complete",
            actionable=preview_status == "ready",
            blocking_reason=preview_block,
        )
    )

    approval_complete = bool(proposal_commit is not None and proposal_commit.can_commit) or commit_complete
    if approval_complete:
        approval_status = "complete"
    elif approval_pending:
        approval_status = "active"
    elif approval_ready or has_preview:
        approval_status = "ready"
    else:
        approval_status = "waiting"
    approval_block = None if approval_status != "waiting" else ui_text("journey.reason.approval_requires_preview", app_language=app_language, fallback_text="Preview must exist before approval")
    steps.append(
        ProductFlowJourneyStepView(
            step_id="approval",
            step_label=ui_text("journey.step.approval", app_language=app_language, fallback_text="Approval"),
            step_status=approval_status,
            step_status_label=_status_label(approval_status, app_language=app_language),
            target_ref=(proposal_commit.summary.current_approval_id if proposal_commit is not None else None),
            preferred_workspace_id="node_configuration",
            preferred_panel_id="designer",
            complete=approval_status == "complete",
            actionable=approval_status in {"ready", "active"},
            blocking_reason=approval_block,
        )
    )

    if commit_complete:
        commit_status = "complete"
    elif proposal_commit is not None and proposal_commit.can_commit:
        commit_status = "ready"
    elif has_preview or approval_ready:
        commit_status = "blocked"
    else:
        commit_status = "waiting"
    commit_block = None
    if commit_status == "blocked":
        commit_block = proposal_commit.summary.next_step_label if proposal_commit is not None else ui_text("journey.reason.commit_requires_approval", app_language=app_language, fallback_text="Approval must be resolved before commit")
    elif commit_status == "waiting":
        commit_block = ui_text("journey.reason.commit_requires_review", app_language=app_language, fallback_text="Review flow must reach approval before commit")
    commit_ref = None
    if proposal_commit is not None and proposal_commit.storage is not None and proposal_commit.storage.commit_snapshot_card is not None:
        commit_ref = proposal_commit.storage.commit_snapshot_card.commit_id
    elif execution_launch is not None:
        commit_ref = execution_launch.summary.commit_anchor_ref
    steps.append(
        ProductFlowJourneyStepView(
            step_id="commit_snapshot",
            step_label=ui_text("journey.step.commit_snapshot", app_language=app_language, fallback_text="Commit snapshot"),
            step_status=commit_status,
            step_status_label=_status_label(commit_status, app_language=app_language),
            target_ref=commit_ref,
            preferred_workspace_id="node_configuration",
            preferred_panel_id="storage",
            complete=commit_status == "complete",
            actionable=commit_status == "ready",
            blocking_reason=commit_block,
        )
    )

    if live_run:
        run_status = "active"
    elif run_complete:
        run_status = "complete"
    elif execution_launch is not None and execution_launch.can_launch:
        run_status = "ready"
    elif commit_complete or source_role == "working_save":
        run_status = "blocked"
    else:
        run_status = "waiting"
    run_block = None
    if run_status == "blocked":
        run_block = execution_launch.summary.next_step_label if execution_launch is not None else ui_text("journey.reason.run_requires_commit", app_language=app_language, fallback_text="A runnable target is required before launch")
    elif run_status == "waiting":
        run_block = ui_text("journey.reason.run_requires_commit", app_language=app_language, fallback_text="A runnable target is required before launch")
    steps.append(
        ProductFlowJourneyStepView(
            step_id="run_current",
            step_label=ui_text("journey.step.run_current", app_language=app_language, fallback_text="Run current"),
            step_status=run_status,
            step_status_label=_status_label(run_status, app_language=app_language),
            target_ref=(execution_launch.summary.run_id if execution_launch is not None else None),
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id="execution",
            complete=run_status == "complete",
            actionable=run_status in {"ready", "active"},
            blocking_reason=run_block,
        )
    )

    if live_run:
        observe_status = "active"
    elif observability_ready:
        observe_status = "complete"
    elif run_complete:
        observe_status = "ready"
    else:
        observe_status = "waiting"
    observe_block = None if observe_status != "waiting" else ui_text("journey.reason.observe_requires_run", app_language=app_language, fallback_text="Run output is required before trace, artifacts, and diff follow-through")
    steps.append(
        ProductFlowJourneyStepView(
            step_id="observe_results",
            step_label=ui_text("journey.step.observe_results", app_language=app_language, fallback_text="Trace, artifacts, and diff"),
            step_status=observe_status,
            step_status_label=_status_label(observe_status, app_language=app_language),
            target_ref=(execution_launch.summary.run_id if execution_launch is not None else None),
            preferred_workspace_id="runtime_monitoring",
            preferred_panel_id=("trace_timeline" if live_run else "artifact"),
            complete=observe_status == "complete",
            actionable=observe_status in {"ready", "active"},
            blocking_reason=observe_block,
        )
    )

    completed_step_count = sum(1 for step in steps if step.complete)
    ready_step_count = sum(1 for step in steps if step.actionable)
    blocked_step_count = sum(1 for step in steps if step.step_status == "blocked")

    current_step = next((step for step in steps if step.step_status == "active"), None)
    if prefer_active_workflow_focus and current_step is None and workflow_hub is not None and workflow_hub.active_workflow_id == "proposal_commit":
        review_ids = {"designer_request", "preview_review", "approval", "commit_snapshot"}
        current_step = next((step for step in steps if step.step_id in review_ids and (not step.complete or step.actionable)), None)
        if current_step is None:
            current_step = next((step for step in steps if step.step_id == "commit_snapshot"), None)
    if prefer_active_workflow_focus and current_step is None and workflow_hub is not None and workflow_hub.active_workflow_id == "execution_launch":
        run_ids = {"run_current", "observe_results"}
        current_step = next((step for step in steps if step.step_id in run_ids and (step.step_status == "active" or step.actionable or not step.complete)), None)
        if current_step is None:
            current_step = next((step for step in steps if step.step_id == "observe_results"), None)
    if current_step is None:
        current_step = next((step for step in steps if not step.complete), steps[-1] if steps else None)

    if not steps:
        journey_status = "empty"
    elif live_run:
        journey_status = "live"
    elif blocked_step_count:
        journey_status = "blocked"
    elif completed_step_count == len(steps):
        journey_status = "complete"
    else:
        journey_status = "ready"

    if journey_status == "complete" and not (prefer_active_workflow_focus and workflow_hub is not None and workflow_hub.active_workflow_id == "proposal_commit"):
        current_step = next((step for step in steps if step.step_id == "observe_results"), current_step)

    return ProductFlowJourneyViewModel(
        journey_status=journey_status,
        journey_status_label=ui_text(f"journey.status.{journey_status}", app_language=app_language, fallback_text=journey_status.replace("_", " ").title()),
        source_role=source_role,
        current_step_id=current_step.step_id if current_step is not None else "designer_request",
        ready_step_count=ready_step_count,
        blocked_step_count=blocked_step_count,
        completed_step_count=completed_step_count,
        steps=steps,
        explanation=explanation,
    )


__all__ = [
    "ProductFlowJourneyStepView",
    "ProductFlowJourneyViewModel",
    "read_product_flow_journey_view_model",
]
