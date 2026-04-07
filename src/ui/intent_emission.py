from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_interaction_hub import BuilderInteractionHubViewModel, read_builder_interaction_hub_view_model


@dataclass(frozen=True)
class BuilderIntentEmissionView:
    emission_id: str
    action_id: str
    label: str
    emission_type: str
    target_domain: str
    payload_contract_id: str
    emit_allowed: bool
    reason_blocked: str | None = None
    requires_confirmation: bool = False
    emission_preview: str | None = None


@dataclass(frozen=True)
class IntentEmissionViewModel:
    emission_status: str = "ready"
    source_role: str = "none"
    recommended_action_id: str | None = None
    emissions: list[BuilderIntentEmissionView] = field(default_factory=list)
    enabled_emission_count: int = 0
    blocked_emission_count: int = 0
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


def _emission_template(action_id: str) -> tuple[str, str, str, str]:
    mapping = {
        "save_working_save": ("storage_intent", "storage", "working_save.persist", "Persist current working save"),
        "review_draft": ("review_intent", "designer", "proposal.review_request", "Request draft review and validation"),
        "commit_snapshot": ("commit_intent", "storage", "commit.snapshot_request", "Create approved commit snapshot"),
        "run_current": ("execution_intent", "execution", "execution.launch_request", "Launch execution for current target"),
        "cancel_run": ("execution_control_intent", "execution", "execution.cancel_request", "Cancel active execution"),
        "replay_latest": ("execution_control_intent", "execution", "execution.replay_request", "Replay latest execution record"),
        "open_diff": ("comparison_intent", "comparison", "comparison.diff_request", "Open comparison or diff view"),
        "approve_for_commit": ("approval_decision_intent", "designer", "approval.decision_request", "Approve current designer proposal"),
        "request_revision": ("designer_revision_intent", "designer", "proposal.revision_request", "Request revision for current proposal"),
    }
    return mapping.get(action_id, ("builder_intent", "builder", f"builder.{action_id}", f"Emit intent for {action_id}"))


def read_intent_emission_view_model(
    source: SourceLike,
    *,
    interaction_hub: BuilderInteractionHubViewModel | None = None,
    explanation: str | None = None,
) -> IntentEmissionViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    interaction_hub = interaction_hub or read_builder_interaction_hub_view_model(source_unwrapped)

    emissions: list[BuilderIntentEmissionView] = []
    for route in interaction_hub.command_routing.routes if interaction_hub.command_routing is not None else []:
        emission_type, target_domain, payload_contract_id, preview = _emission_template(route.action_id)
        emissions.append(
            BuilderIntentEmissionView(
                emission_id=f"emit:{route.action_id}",
                action_id=route.action_id,
                label=route.label,
                emission_type=emission_type,
                target_domain=target_domain,
                payload_contract_id=payload_contract_id,
                emit_allowed=route.enabled,
                reason_blocked=route.reason_disabled,
                requires_confirmation=route.requires_confirmation,
                emission_preview=preview,
            )
        )

    enabled_emission_count = sum(1 for item in emissions if item.emit_allowed)
    blocked_emission_count = len(emissions) - enabled_emission_count
    if not emissions:
        emission_status = "empty"
    elif blocked_emission_count == len(emissions):
        emission_status = "blocked"
    elif blocked_emission_count:
        emission_status = "attention"
    else:
        emission_status = "ready"

    return IntentEmissionViewModel(
        emission_status=emission_status,
        source_role=source_role,
        recommended_action_id=interaction_hub.recommended_action_id,
        emissions=emissions,
        enabled_emission_count=enabled_emission_count,
        blocked_emission_count=blocked_emission_count,
        explanation=explanation,
    )


__all__ = [
    "BuilderIntentEmissionView",
    "IntentEmissionViewModel",
    "read_intent_emission_view_model",
]
