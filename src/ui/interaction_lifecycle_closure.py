from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_execution_adapter_hub import BuilderExecutionAdapterHubViewModel, read_builder_execution_adapter_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.end_user_command_flows import EndUserCommandFlowViewModel, read_end_user_command_flow_view_model


@dataclass(frozen=True)
class LifecycleClosureStageView:
    stage_id: str
    stage_label: str
    stage_status: str
    stage_status_label: str
    closed: bool
    closeable: bool
    recommended_flow_id: str | None = None
    open_requirement: str | None = None


@dataclass(frozen=True)
class InteractionLifecycleClosureViewModel:
    closure_status: str = "ready"
    closure_status_label: str | None = None
    source_role: str = "none"
    current_stage_id: str = "drafting"
    current_stage_closed: bool = False
    next_stage_ready: bool = False
    terminal_completion_ready: bool = False
    open_requirement_count: int = 0
    stages: list[LifecycleClosureStageView] = field(default_factory=list)
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


def _find_flow(flows: EndUserCommandFlowViewModel, action_ids: tuple[str, ...]):
    for action_id in action_ids:
        flow = next((item for item in flows.flows if item.action_id == action_id), None)
        if flow is not None:
            return flow
    return None


def _stage_requirements_for(*, source_role: str) -> dict[str, tuple[str, ...]]:
    if source_role == "commit_snapshot":
        return {
            "drafting": ("open_latest_commit",),
            "review": ("open_latest_commit",),
            "commit": ("open_latest_commit", "select_rollback_target"),
            "execution": ("run_from_commit",),
            "history": ("open_latest_run", "open_trace", "open_artifacts", "compare_runs"),
        }
    if source_role == "execution_record":
        return {
            "drafting": ("open_latest_run",),
            "review": ("open_latest_run",),
            "commit": ("open_latest_run",),
            "execution": ("open_latest_run",),
            "history": ("open_trace", "open_artifacts", "compare_runs", "open_latest_run"),
        }
    return {
        "drafting": ("review_draft",),
        "review": ("approve_for_commit",),
        "commit": ("commit_snapshot",),
        "execution": ("run_current", "run_from_commit"),
        "history": ("replay_latest", "open_latest_run", "open_trace", "open_artifacts", "compare_runs"),
    }


def read_interaction_lifecycle_closure_view_model(
    source: SourceLike,
    *,
    execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None,
    end_user_flows: EndUserCommandFlowViewModel | None = None,
    explanation: str | None = None,
) -> InteractionLifecycleClosureViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    execution_adapter_hub = execution_adapter_hub or read_builder_execution_adapter_hub_view_model(source_unwrapped)
    end_user_flows = end_user_flows or read_end_user_command_flow_view_model(source_unwrapped, execution_adapter_hub=execution_adapter_hub)

    lifecycle = execution_adapter_hub.dispatch_hub.lifecycle if execution_adapter_hub.dispatch_hub is not None else None
    current_stage_id = lifecycle.current_stage_id if lifecycle is not None else "drafting"

    stage_requirements = _stage_requirements_for(source_role=source_role)

    stages: list[LifecycleClosureStageView] = []
    for stage in lifecycle.stages if lifecycle is not None else []:
        required_action_ids = stage_requirements.get(stage.stage_id, ())
        flow = _find_flow(end_user_flows, required_action_ids) if required_action_ids else None
        closed = stage.status == "completed" or (flow is not None and flow.closure_ready and stage.stage_id != current_stage_id)
        closeable = flow is not None and flow.execute_allowed
        open_requirement = None if closed or closeable else ((flow.action_id if flow is not None else (required_action_ids[0] if required_action_ids else None)) or "no_requirement")
        stages.append(
            LifecycleClosureStageView(
                stage_id=stage.stage_id,
                stage_label=ui_text(f"interaction.stage.{stage.stage_id}", app_language=app_language, fallback_text=stage.stage_id.replace("_", " ")),
                stage_status=stage.status,
                stage_status_label=ui_text(f"interaction.stage_status.{stage.status}", app_language=app_language, fallback_text=stage.status.replace("_", " ")),
                closed=closed,
                closeable=closeable,
                recommended_flow_id=flow.flow_id if flow is not None else None,
                open_requirement=open_requirement,
            )
        )

    current_stage = next((item for item in stages if item.stage_id == current_stage_id), None)
    current_stage_closed = current_stage.closed if current_stage is not None else False
    next_stage_ready = any(item.stage_id != current_stage_id and item.closeable for item in stages)
    terminal_completion_ready = bool(lifecycle is not None and lifecycle.terminal) or source_role == "execution_record"
    open_requirement_count = sum(1 for item in stages if item.open_requirement is not None)

    if not stages:
        closure_status = "empty"
    elif open_requirement_count and not next_stage_ready:
        closure_status = "blocked"
    elif open_requirement_count:
        closure_status = "attention"
    else:
        closure_status = "ready"

    return InteractionLifecycleClosureViewModel(
        closure_status=closure_status,
        closure_status_label=ui_text(f"hub.status.{closure_status}", app_language=app_language, fallback_text=closure_status.replace("_", " ")),
        source_role=source_role,
        current_stage_id=current_stage_id,
        current_stage_closed=current_stage_closed,
        next_stage_ready=next_stage_ready,
        terminal_completion_ready=terminal_completion_ready,
        open_requirement_count=open_requirement_count,
        stages=stages,
        explanation=explanation,
    )


__all__ = [
    "LifecycleClosureStageView",
    "InteractionLifecycleClosureViewModel",
    "read_interaction_lifecycle_closure_view_model",
]
