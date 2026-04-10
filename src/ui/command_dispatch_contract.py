from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.command_routing import BuilderCommandRoutingViewModel, read_builder_command_routing_view_model
from src.ui.intent_emission import IntentEmissionViewModel, read_intent_emission_view_model
from src.ui.builder_interaction_hub import BuilderInteractionHubViewModel, read_builder_interaction_hub_view_model


@dataclass(frozen=True)
class DispatchFieldView:
    field_name: str
    required: bool = True
    source_hint: str | None = None


@dataclass(frozen=True)
class CommandDispatchContractView:
    contract_id: str
    action_id: str
    command_type: str
    dispatch_mode: str
    boundary_target: str
    payload_contract_id: str
    required_fields: list[DispatchFieldView] = field(default_factory=list)
    dispatch_allowed: bool = False
    reason_blocked: str | None = None
    requires_confirmation: bool = False


@dataclass(frozen=True)
class CommandDispatchContractViewModel:
    dispatch_status: str = "ready"
    source_role: str = "none"
    contracts: list[CommandDispatchContractView] = field(default_factory=list)
    enabled_dispatch_count: int = 0
    blocked_dispatch_count: int = 0
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


def _dispatch_mode(action_id: str, target_domain: str) -> str:
    if action_id in {"approve_for_commit", "request_revision"}:
        return "designer_flow"
    if target_domain == "execution":
        return "execution_gateway"
    if target_domain == "storage":
        return "storage_gateway"
    if target_domain == "comparison":
        return "ui_only"
    return "interaction_hub"


def _required_fields(action_id: str) -> list[DispatchFieldView]:
    mapping = {
        "save_working_save": [DispatchFieldView("working_save_id", True, "storage.current_working_save"), DispatchFieldView("storage_role", True, "adapter.source_role")],
        "review_draft": [DispatchFieldView("working_save_id", True, "storage.current_working_save"), DispatchFieldView("validation_status", True, "validation.overall_status")],
        "commit_snapshot": [DispatchFieldView("working_save_id", True, "storage.current_working_save"), DispatchFieldView("approval_id", False, "designer.approval_state"), DispatchFieldView("review_state", True, "proposal_commit.summary")],
        "open_latest_commit": [DispatchFieldView("commit_id", True, "storage.latest_commit_ref")],
        "select_rollback_target": [DispatchFieldView("commit_id", True, "storage.rollback_target")],
        "run_current": [DispatchFieldView("target_ref", True, "storage.active_target"), DispatchFieldView("validation_status", True, "validation.overall_status")],
        "run_from_commit": [DispatchFieldView("commit_id", True, "storage.latest_commit_ref"), DispatchFieldView("validation_status", False, "validation.overall_status")],
        "cancel_run": [DispatchFieldView("run_id", True, "execution.current_run")],
        "replay_latest": [DispatchFieldView("run_id", True, "storage.execution_record")],
        "open_latest_run": [DispatchFieldView("run_id", True, "storage.execution_record")],
        "open_trace": [DispatchFieldView("run_id", True, "trace.current_run")],
        "open_artifacts": [DispatchFieldView("run_id", True, "artifact.current_run")],
        "open_diff": [DispatchFieldView("source_ref", True, "diff.source"), DispatchFieldView("target_ref", True, "diff.target")],
        "compare_runs": [DispatchFieldView("run_id", True, "storage.execution_record"), DispatchFieldView("comparison_target_ref", False, "storage.recent_execution_refs")],
        "approve_for_commit": [DispatchFieldView("approval_id", True, "designer.approval_state"), DispatchFieldView("decision", True, "ui.user_decision")],
        "request_revision": [DispatchFieldView("approval_id", False, "designer.approval_state"), DispatchFieldView("revision_reason", True, "ui.user_input")],
    }
    return mapping.get(action_id, [DispatchFieldView("action_id", True, "interaction.selected_action")])


def read_command_dispatch_contract_view_model(
    source: SourceLike,
    *,
    interaction_hub: BuilderInteractionHubViewModel | None = None,
    command_routing: BuilderCommandRoutingViewModel | None = None,
    intent_emission: IntentEmissionViewModel | None = None,
    explanation: str | None = None,
) -> CommandDispatchContractViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    interaction_hub = interaction_hub or read_builder_interaction_hub_view_model(source_unwrapped)
    command_routing = command_routing or interaction_hub.command_routing or read_builder_command_routing_view_model(source_unwrapped)
    intent_emission = intent_emission or read_intent_emission_view_model(source_unwrapped, interaction_hub=interaction_hub)
    emission_by_action = {item.action_id: item for item in intent_emission.emissions}

    contracts: list[CommandDispatchContractView] = []
    for route in command_routing.routes:
        emission = emission_by_action.get(route.action_id)
        dispatch_allowed = route.enabled and (emission.emit_allowed if emission is not None else True)
        contracts.append(
            CommandDispatchContractView(
                contract_id=f"dispatch:{route.action_id}",
                action_id=route.action_id,
                command_type=route.command_type,
                dispatch_mode=_dispatch_mode(route.action_id, route.target_domain),
                boundary_target=route.engine_boundary,
                payload_contract_id=emission.payload_contract_id if emission is not None else f"builder.{route.action_id}",
                required_fields=_required_fields(route.action_id),
                dispatch_allowed=dispatch_allowed,
                reason_blocked=route.reason_disabled if not dispatch_allowed else None,
                requires_confirmation=route.requires_confirmation,
            )
        )

    enabled_dispatch_count = sum(1 for item in contracts if item.dispatch_allowed)
    blocked_dispatch_count = len(contracts) - enabled_dispatch_count
    if not contracts:
        dispatch_status = "empty"
    elif interaction_hub.hub_status == "blocked" or blocked_dispatch_count == len(contracts):
        dispatch_status = "blocked"
    elif (source_role == "execution_record" or interaction_hub.hub_status == "terminal") and enabled_dispatch_count > 0:
        dispatch_status = "terminal"
    elif interaction_hub.hub_status == "attention" or blocked_dispatch_count:
        dispatch_status = "attention"
    else:
        dispatch_status = "ready"

    return CommandDispatchContractViewModel(
        dispatch_status=dispatch_status,
        source_role=source_role,
        contracts=contracts,
        enabled_dispatch_count=enabled_dispatch_count,
        blocked_dispatch_count=blocked_dispatch_count,
        explanation=explanation,
    )


__all__ = [
    "DispatchFieldView",
    "CommandDispatchContractView",
    "CommandDispatchContractViewModel",
    "read_command_dispatch_contract_view_model",
]
