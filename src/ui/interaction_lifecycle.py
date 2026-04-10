from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_interaction_hub import BuilderInteractionHubViewModel, read_builder_interaction_hub_view_model
from src.ui.command_dispatch_contract import CommandDispatchContractViewModel, read_command_dispatch_contract_view_model
from src.ui.i18n import ui_language_from_sources, ui_text


@dataclass(frozen=True)
class InteractionLifecycleStageView:
    stage_id: str
    label: str
    status: str
    focus_workspace_id: str
    entry_action_id: str | None = None
    blocking_count: int = 0


@dataclass(frozen=True)
class InteractionLifecycleViewModel:
    lifecycle_status: str = "ready"
    source_role: str = "none"
    current_stage_id: str = "drafting"
    next_stage_id: str | None = None
    terminal: bool = False
    can_advance: bool = False
    stages: list[InteractionLifecycleStageView] = field(default_factory=list)
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


def _entry_action_for(stage_id: str, *, source_role: str) -> str | None:
    if source_role == "commit_snapshot":
        mapping = {
            "drafting": "open_latest_commit",
            "review": "open_latest_commit",
            "commit": "open_latest_commit",
            "execution": "run_from_commit",
            "history": "open_latest_run",
        }
        return mapping.get(stage_id)
    if source_role == "execution_record":
        mapping = {
            "drafting": "open_latest_run",
            "review": "open_latest_run",
            "commit": "open_latest_run",
            "execution": "open_latest_run",
            "history": "open_trace",
        }
        return mapping.get(stage_id)
    mapping = {
        "drafting": "save_working_save",
        "review": "review_draft",
        "commit": "commit_snapshot",
        "execution": "run_current",
        "history": "replay_latest",
    }
    return mapping.get(stage_id)


def _status_for(stage_id: str, *, interaction_hub: BuilderInteractionHubViewModel, dispatch_contract: CommandDispatchContractViewModel) -> str:
    source_role = interaction_hub.source_role
    proposal = interaction_hub.workflow_hub.proposal_commit
    execution_workflow = interaction_hub.workflow_hub.execution_launch
    if source_role == "execution_record":
        if stage_id in {"drafting", "review", "commit"}:
            return "completed"
        if stage_id == "execution":
            return "active" if execution_workflow.workflow_status == "live_monitoring" else "completed"
        if stage_id == "history":
            return "active"
        return "waiting"
    if source_role == "commit_snapshot":
        if stage_id in {"drafting", "review", "commit"}:
            return "completed"
        if stage_id == "execution":
            if execution_workflow.workflow_status == "blocked":
                return "blocked"
            return "active" if execution_workflow.workflow_status == "live_monitoring" else ("available" if interaction_hub.workflow_hub.execution_launch.can_launch else "waiting")
        if stage_id == "history":
            return "active" if execution_workflow.can_replay else "waiting"
        return "waiting"
    if stage_id == "drafting":
        return "active" if interaction_hub.workflow_hub.active_workflow_id == "proposal_commit" and proposal.workflow_status in {"idle", "review_ready", "proposal_in_progress"} else "completed"
    if stage_id == "review":
        if proposal.workflow_status == "blocked":
            return "blocked"
        if proposal.workflow_status in {"preview_ready", "awaiting_approval", "commit_ready"}:
            return "active"
        return "available"
    if stage_id == "commit":
        commit_dispatch = next((item for item in dispatch_contract.contracts if item.action_id == "commit_snapshot"), None)
        if commit_dispatch is not None and commit_dispatch.dispatch_allowed:
            return "available"
        if proposal.workflow_status == "committed_context":
            return "completed"
        return "waiting"
    if stage_id == "execution":
        if execution_workflow.workflow_status == "blocked":
            return "blocked"
        if execution_workflow.workflow_status == "live_monitoring":
            return "active"
        run_dispatch = next((item for item in dispatch_contract.contracts if item.action_id in {"run_current", "run_from_commit"} and item.dispatch_allowed), None)
        if run_dispatch is not None:
            return "available"
        return "waiting"
    if stage_id == "history":
        return "active" if execution_workflow.can_replay or interaction_hub.source_role == "execution_record" else "waiting"
    return "waiting"


def read_interaction_lifecycle_view_model(
    source: SourceLike,
    *,
    interaction_hub: BuilderInteractionHubViewModel | None = None,
    dispatch_contract: CommandDispatchContractViewModel | None = None,
    explanation: str | None = None,
) -> InteractionLifecycleViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    interaction_hub = interaction_hub or read_builder_interaction_hub_view_model(source_unwrapped)
    dispatch_contract = dispatch_contract or read_command_dispatch_contract_view_model(source_unwrapped, interaction_hub=interaction_hub)

    proposal_commit = interaction_hub.workflow_hub.proposal_commit if interaction_hub.workflow_hub is not None else None
    execution_launch = interaction_hub.workflow_hub.execution_launch if interaction_hub.workflow_hub is not None else None
    proposal_blocking_count = proposal_commit.summary.blocking_count if proposal_commit is not None else 0
    proposal_pending_decisions = proposal_commit.summary.pending_decision_count if proposal_commit is not None else 0
    execution_blocking_count = execution_launch.summary.blocking_count if execution_launch is not None else 0

    stages = [
        InteractionLifecycleStageView("drafting", ui_text("interaction.stage.drafting", app_language=app_language, fallback_text="Drafting"), _status_for("drafting", interaction_hub=interaction_hub, dispatch_contract=dispatch_contract), "visual_editor", _entry_action_for("drafting", source_role=source_role), proposal_blocking_count),
        InteractionLifecycleStageView("review", ui_text("interaction.stage.review", app_language=app_language, fallback_text="Review & Approval"), _status_for("review", interaction_hub=interaction_hub, dispatch_contract=dispatch_contract), "node_configuration", _entry_action_for("review", source_role=source_role), proposal_blocking_count),
        InteractionLifecycleStageView("commit", ui_text("interaction.stage.commit", app_language=app_language, fallback_text="Commit"), _status_for("commit", interaction_hub=interaction_hub, dispatch_contract=dispatch_contract), "visual_editor", _entry_action_for("commit", source_role=source_role), proposal_pending_decisions),
        InteractionLifecycleStageView("execution", ui_text("interaction.stage.execution", app_language=app_language, fallback_text="Execution"), _status_for("execution", interaction_hub=interaction_hub, dispatch_contract=dispatch_contract), "runtime_monitoring", _entry_action_for("execution", source_role=source_role), execution_blocking_count),
        InteractionLifecycleStageView("history", ui_text("interaction.stage.history", app_language=app_language, fallback_text="History & Replay"), _status_for("history", interaction_hub=interaction_hub, dispatch_contract=dispatch_contract), "runtime_monitoring", _entry_action_for("history", source_role=source_role), 0),
    ]

    current_stage = next((stage.stage_id for stage in stages if stage.status == "active"), None)
    if current_stage is None:
        current_stage = next((stage.stage_id for stage in stages if stage.status == "available"), "drafting")
    next_stage = None
    for stage in stages:
        if stage.stage_id == current_stage:
            continue
        if stage.status in {"available", "active"}:
            next_stage = stage.stage_id
            break
    terminal = source_role == "execution_record"
    can_advance = any(stage.status == "available" for stage in stages if stage.stage_id != current_stage)
    lifecycle_status = "terminal" if terminal else ("attention" if any(stage.status == "blocked" for stage in stages) else "ready")

    return InteractionLifecycleViewModel(
        lifecycle_status=lifecycle_status,
        source_role=source_role,
        current_stage_id=current_stage,
        next_stage_id=next_stage,
        terminal=terminal,
        can_advance=can_advance,
        stages=stages,
        explanation=explanation,
    )


__all__ = [
    "InteractionLifecycleStageView",
    "InteractionLifecycleViewModel",
    "read_interaction_lifecycle_view_model",
]
