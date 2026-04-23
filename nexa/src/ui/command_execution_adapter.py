from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_dispatch_hub import BuilderDispatchHubViewModel, read_builder_dispatch_hub_view_model


@dataclass(frozen=True)
class CommandExecutionAdapterView:
    adapter_id: str
    action_id: str
    execution_adapter_id: str
    adapter_kind: str
    engine_boundary: str
    dispatch_mode: str
    dry_run_available: bool = False
    side_effect_scope: str = "none"
    execute_allowed: bool = False
    reason_blocked: str | None = None
    expected_status_change: str | None = None


@dataclass(frozen=True)
class CommandExecutionAdapterViewModel:
    adapter_status: str = "ready"
    source_role: str = "none"
    adapters: list[CommandExecutionAdapterView] = field(default_factory=list)
    enabled_adapter_count: int = 0
    blocked_adapter_count: int = 0
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


def _adapter_kind(boundary: str, action_id: str) -> tuple[str, bool, str, str | None]:
    mapping = {
        "working_save_api": ("storage_write_adapter", True, "working_save", "draft_persisted"),
        "designer_flow": ("designer_flow_adapter", True, "proposal", "review_requested"),
        "commit_gateway": ("commit_gateway_adapter", True, "commit_snapshot", "commit_created"),
        "approval_flow": ("approval_flow_adapter", True, "approval", "approval_updated"),
        "execution_runner": ("execution_control_adapter", True, "execution", "execution_state_changed"),
        "execution_replay": ("execution_replay_adapter", False, "history", "history_opened"),
        "diff_engine": ("comparison_adapter", False, "comparison", "diff_opened"),
        "ui_boundary": ("ui_navigation_adapter", False, "ui", "ui_state_changed"),
    }
    if boundary in mapping:
        return mapping[boundary]
    if action_id.startswith("commit"):
        return ("commit_gateway_adapter", True, "commit_snapshot", "commit_created")
    return ("generic_engine_adapter", False, "none", None)


def read_command_execution_adapter_view_model(
    source: SourceLike,
    *,
    dispatch_hub: BuilderDispatchHubViewModel | None = None,
    explanation: str | None = None,
) -> CommandExecutionAdapterViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    dispatch_hub = dispatch_hub or read_builder_dispatch_hub_view_model(source_unwrapped)

    adapters: list[CommandExecutionAdapterView] = []
    for contract in dispatch_hub.dispatch_contract.contracts if dispatch_hub.dispatch_contract is not None else []:
        adapter_kind, dry_run_available, side_effect_scope, expected_status_change = _adapter_kind(
            contract.boundary_target,
            contract.action_id,
        )
        adapters.append(
            CommandExecutionAdapterView(
                adapter_id=f"adapter:{contract.action_id}",
                action_id=contract.action_id,
                execution_adapter_id=f"{adapter_kind}:{contract.action_id}",
                adapter_kind=adapter_kind,
                engine_boundary=contract.boundary_target,
                dispatch_mode=contract.dispatch_mode,
                dry_run_available=dry_run_available,
                side_effect_scope=side_effect_scope,
                execute_allowed=contract.dispatch_allowed,
                reason_blocked=contract.reason_blocked if not contract.dispatch_allowed else None,
                expected_status_change=expected_status_change,
            )
        )

    enabled_adapter_count = sum(1 for item in adapters if item.execute_allowed)
    blocked_adapter_count = len(adapters) - enabled_adapter_count
    if not adapters:
        adapter_status = "empty"
    elif dispatch_hub.hub_status == "blocked" or blocked_adapter_count == len(adapters):
        adapter_status = "blocked"
    elif (source_role == "execution_record" or dispatch_hub.hub_status == "terminal") and enabled_adapter_count > 0:
        adapter_status = "terminal"
    elif dispatch_hub.hub_status == "attention" or blocked_adapter_count:
        adapter_status = "attention"
    else:
        adapter_status = "ready"

    return CommandExecutionAdapterViewModel(
        adapter_status=adapter_status,
        source_role=source_role,
        adapters=adapters,
        enabled_adapter_count=enabled_adapter_count,
        blocked_adapter_count=blocked_adapter_count,
        explanation=explanation,
    )


__all__ = [
    "CommandExecutionAdapterView",
    "CommandExecutionAdapterViewModel",
    "read_command_execution_adapter_view_model",
]
