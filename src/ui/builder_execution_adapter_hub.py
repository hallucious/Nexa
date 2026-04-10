from __future__ import annotations

from dataclasses import dataclass

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.builder_dispatch_hub import BuilderDispatchHubViewModel, read_builder_dispatch_hub_view_model
from src.ui.command_execution_adapter import CommandExecutionAdapterViewModel, read_command_execution_adapter_view_model
from src.ui.interaction_state_changes import InteractionStateChangeViewModel, read_interaction_state_change_view_model


@dataclass(frozen=True)
class BuilderExecutionAdapterHubViewModel:
    hub_status: str = "ready"
    hub_status_label: str | None = None
    source_role: str = "none"
    dispatch_hub: BuilderDispatchHubViewModel | None = None
    execution_adapters: CommandExecutionAdapterViewModel | None = None
    state_changes: InteractionStateChangeViewModel | None = None
    recommended_action_id: str | None = None
    executable_action_count: int = 0
    state_change_ready_count: int = 0
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


def read_builder_execution_adapter_hub_view_model(
    source: SourceLike,
    *,
    dispatch_hub: BuilderDispatchHubViewModel | None = None,
    explanation: str | None = None,
) -> BuilderExecutionAdapterHubViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    dispatch_hub = dispatch_hub or read_builder_dispatch_hub_view_model(source_unwrapped)
    execution_adapters = read_command_execution_adapter_view_model(source_unwrapped, dispatch_hub=dispatch_hub)
    state_changes = read_interaction_state_change_view_model(source_unwrapped, dispatch_hub=dispatch_hub, execution_adapters=execution_adapters)

    if dispatch_hub.lifecycle is not None and dispatch_hub.lifecycle.terminal:
        hub_status = "terminal"
    elif execution_adapters.adapter_status == "blocked":
        hub_status = "blocked"
    elif execution_adapters.adapter_status == "attention" or state_changes.state_change_status == "attention":
        hub_status = "attention"
    else:
        hub_status = "ready"

    return BuilderExecutionAdapterHubViewModel(
        hub_status=hub_status,
        hub_status_label=ui_text(f"hub.status.{hub_status}", app_language=app_language, fallback_text=hub_status.replace("_", " ")),
        source_role=source_role,
        dispatch_hub=dispatch_hub,
        execution_adapters=execution_adapters,
        state_changes=state_changes,
        recommended_action_id=dispatch_hub.recommended_action_id,
        executable_action_count=execution_adapters.enabled_adapter_count,
        state_change_ready_count=state_changes.enabled_change_count,
        explanation=explanation,
    )


__all__ = [
    "BuilderExecutionAdapterHubViewModel",
    "read_builder_execution_adapter_hub_view_model",
]
