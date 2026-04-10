from __future__ import annotations

from dataclasses import dataclass

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.builder_interaction_hub import BuilderInteractionHubViewModel, read_builder_interaction_hub_view_model
from src.ui.command_dispatch_contract import CommandDispatchContractViewModel, read_command_dispatch_contract_view_model
from src.ui.intent_emission import IntentEmissionViewModel, read_intent_emission_view_model
from src.ui.interaction_lifecycle import InteractionLifecycleViewModel, read_interaction_lifecycle_view_model


@dataclass(frozen=True)
class BuilderDispatchHubViewModel:
    hub_status: str = "ready"
    hub_status_label: str | None = None
    source_role: str = "none"
    interaction_hub: BuilderInteractionHubViewModel | None = None
    intent_emission: IntentEmissionViewModel | None = None
    dispatch_contract: CommandDispatchContractViewModel | None = None
    lifecycle: InteractionLifecycleViewModel | None = None
    recommended_action_id: str | None = None
    enabled_dispatch_count: int = 0
    can_progress_lifecycle: bool = False
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


def read_builder_dispatch_hub_view_model(
    source: SourceLike,
    *,
    interaction_hub: BuilderInteractionHubViewModel | None = None,
    explanation: str | None = None,
) -> BuilderDispatchHubViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    interaction_hub = interaction_hub or read_builder_interaction_hub_view_model(source_unwrapped)
    intent_emission = read_intent_emission_view_model(source_unwrapped, interaction_hub=interaction_hub)
    dispatch_contract = read_command_dispatch_contract_view_model(source_unwrapped, interaction_hub=interaction_hub, intent_emission=intent_emission)
    lifecycle = read_interaction_lifecycle_view_model(source_unwrapped, interaction_hub=interaction_hub, dispatch_contract=dispatch_contract)

    if interaction_hub.hub_status == "terminal" or lifecycle.lifecycle_status == "terminal":
        hub_status = "terminal"
    elif interaction_hub.hub_status == "blocked" or dispatch_contract.dispatch_status == "blocked":
        hub_status = "blocked"
    elif interaction_hub.hub_status == "attention" or lifecycle.lifecycle_status == "attention" or intent_emission.emission_status == "attention":
        hub_status = "attention"
    else:
        hub_status = "ready"

    return BuilderDispatchHubViewModel(
        hub_status=hub_status,
        hub_status_label=ui_text(f"hub.status.{hub_status}", app_language=app_language, fallback_text=hub_status.replace("_", " ")),
        source_role=source_role,
        interaction_hub=interaction_hub,
        intent_emission=intent_emission,
        dispatch_contract=dispatch_contract,
        lifecycle=lifecycle,
        recommended_action_id=interaction_hub.recommended_action_id,
        enabled_dispatch_count=dispatch_contract.enabled_dispatch_count,
        can_progress_lifecycle=lifecycle.can_advance,
        explanation=explanation,
    )


__all__ = [
    "BuilderDispatchHubViewModel",
    "read_builder_dispatch_hub_view_model",
]
