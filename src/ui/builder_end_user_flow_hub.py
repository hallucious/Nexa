from __future__ import annotations

from dataclasses import dataclass

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.builder_execution_adapter_hub import BuilderExecutionAdapterHubViewModel, read_builder_execution_adapter_hub_view_model
from src.ui.end_user_command_flows import EndUserCommandFlowViewModel, read_end_user_command_flow_view_model
from src.ui.interaction_lifecycle_closure import InteractionLifecycleClosureViewModel, read_interaction_lifecycle_closure_view_model


@dataclass(frozen=True)
class BuilderEndUserFlowHubViewModel:
    hub_status: str = "ready"
    hub_status_label: str | None = None
    source_role: str = "none"
    execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None
    end_user_flows: EndUserCommandFlowViewModel | None = None
    lifecycle_closure: InteractionLifecycleClosureViewModel | None = None
    recommended_flow_id: str | None = None
    executable_flow_count: int = 0
    closure_open_requirement_count: int = 0
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


def read_builder_end_user_flow_hub_view_model(
    source: SourceLike,
    *,
    execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None,
    explanation: str | None = None,
) -> BuilderEndUserFlowHubViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    execution_adapter_hub = execution_adapter_hub or read_builder_execution_adapter_hub_view_model(source_unwrapped)
    end_user_flows = read_end_user_command_flow_view_model(source_unwrapped, execution_adapter_hub=execution_adapter_hub)
    lifecycle_closure = read_interaction_lifecycle_closure_view_model(
        source_unwrapped,
        execution_adapter_hub=execution_adapter_hub,
        end_user_flows=end_user_flows,
    )

    if lifecycle_closure.terminal_completion_ready or end_user_flows.flow_status == "terminal":
        hub_status = "terminal"
    elif end_user_flows.flow_status == "blocked" or lifecycle_closure.closure_status == "blocked":
        hub_status = "blocked"
    elif end_user_flows.flow_status == "attention" or lifecycle_closure.closure_status == "attention":
        hub_status = "attention"
    else:
        hub_status = "ready"

    return BuilderEndUserFlowHubViewModel(
        hub_status=hub_status,
        hub_status_label=ui_text(f"hub.status.{hub_status}", app_language=app_language, fallback_text=hub_status.replace("_", " ")),
        source_role=source_role,
        execution_adapter_hub=execution_adapter_hub,
        end_user_flows=end_user_flows,
        lifecycle_closure=lifecycle_closure,
        recommended_flow_id=end_user_flows.recommended_flow_id,
        executable_flow_count=end_user_flows.enabled_flow_count,
        closure_open_requirement_count=lifecycle_closure.open_requirement_count,
        explanation=explanation,
    )


__all__ = [
    "BuilderEndUserFlowHubViewModel",
    "read_builder_end_user_flow_hub_view_model",
]
