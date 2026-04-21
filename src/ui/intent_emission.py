from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.builder_interaction_hub import BuilderInteractionHubViewModel, read_builder_interaction_hub_view_model
from src.ui.i18n import ui_language_from_sources, ui_text


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


def _emission_template(action_id: str, *, app_language: str) -> tuple[str, str, str, str]:
    mapping = {
        "save_working_save": ("storage_intent", "storage", "working_save.persist", "Persist current working save"),
        "review_draft": ("review_intent", "designer", "proposal.review_request", "Request draft review and validation"),
        "commit_snapshot": ("commit_intent", "storage", "commit.snapshot_request", "Create approved commit snapshot"),
        "open_latest_commit": ("storage_intent", "storage", "commit.snapshot_inspect_request", "Open latest approved commit snapshot"),
        "select_rollback_target": ("storage_intent", "storage", "commit.rollback_target_select_request", "Select a rollback target from commit history"),
        "run_current": ("execution_intent", "execution", "execution.launch_request", "Launch execution for current target"),
        "run_from_commit": ("execution_intent", "execution", "execution.commit_launch_request", "Launch execution from approved commit snapshot"),
        "cancel_run": ("execution_control_intent", "execution", "execution.cancel_request", "Cancel active execution"),
        "replay_latest": ("execution_control_intent", "execution", "execution.replay_request", "Replay latest execution record"),
        "open_latest_run": ("execution_control_intent", "execution", "execution.history_open_request", "Open latest execution record"),
        "open_trace": ("execution_control_intent", "execution", "execution.trace_open_request", "Open trace timeline for the current run"),
        "open_artifacts": ("execution_control_intent", "execution", "execution.artifacts_open_request", "Open artifacts for the current run"),
        "open_diff": ("comparison_intent", "comparison", "comparison.diff_request", "Open comparison or diff view"),
        "compare_runs": ("comparison_intent", "comparison", "comparison.run_diff_request", "Compare execution runs"),
        "approve_for_commit": ("approval_decision_intent", "designer", "approval.decision_request", "Approve current designer proposal"),
        "request_revision": ("designer_revision_intent", "designer", "proposal.revision_request", "Request revision for current proposal"),
        "open_provider_setup": ("ui_navigation_intent", "ui", "ui.provider_setup_open_request", "Open provider setup guidance"),
        "create_circuit_from_template": ("ui_navigation_intent", "ui", "ui.template_gallery_open_request", "Open starter workflow templates"),
        "open_file_input": ("ui_navigation_intent", "ui", "ui.file_input_open_request", "Open file-based input path"),
        "enter_url_input": ("ui_navigation_intent", "ui", "ui.url_input_open_request", "Open URL-based input path"),
        "review_run_cost": ("ui_navigation_intent", "ui", "ui.execution_cost_review_request", "Open expected run usage review"),
        "watch_run_progress": ("ui_navigation_intent", "ui", "ui.run_progress_focus_request", "Focus the current run progress view"),
        "open_circuit_library": ("ui_navigation_intent", "ui", "ui.workflow_library_open_request", "Open the workflow library"),
        "open_result_history": ("ui_navigation_intent", "ui", "ui.result_history_open_request", "Open recent result history"),
        "open_feedback_channel": ("ui_navigation_intent", "ui", "ui.feedback_channel_open_request", "Open the feedback channel"),
    }
    emission_type, target_domain, payload_contract_id, preview = mapping.get(action_id, ("builder_intent", "builder", f"builder.{action_id}", ui_text("intent.preview.generic", app_language=app_language, fallback_text=f"Emit intent for {action_id}", action_id=action_id)))
    return emission_type, target_domain, payload_contract_id, ui_text(f"intent.preview.{action_id}", app_language=app_language, fallback_text=preview)


def read_intent_emission_view_model(
    source: SourceLike,
    *,
    interaction_hub: BuilderInteractionHubViewModel | None = None,
    explanation: str | None = None,
) -> IntentEmissionViewModel:
    source_unwrapped = _unwrap(source)
    source_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)
    interaction_hub = interaction_hub or read_builder_interaction_hub_view_model(source_unwrapped)

    emissions: list[BuilderIntentEmissionView] = []
    for route in interaction_hub.command_routing.routes if interaction_hub.command_routing is not None else []:
        emission_type, target_domain, payload_contract_id, preview = _emission_template(route.action_id, app_language=app_language)
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
