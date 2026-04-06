from __future__ import annotations

from dataclasses import dataclass, field

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.designer_panel import DesignerPanelViewModel
from src.ui.execution_panel import ExecutionPanelViewModel
from src.ui.storage_panel import StoragePanelViewModel
from src.ui.validation_panel import ValidationPanelViewModel


@dataclass(frozen=True)
class BuilderActionView:
    action_id: str
    label: str
    action_kind: str
    enabled: bool
    reason_disabled: str | None = None
    target_scope: str = "builder_shell"
    destructive: bool = False
    requires_confirmation: bool = False


@dataclass(frozen=True)
class BuilderActionSchemaView:
    schema_status: str = "ready"
    source_role: str = "none"
    primary_actions: list[BuilderActionView] = field(default_factory=list)
    secondary_actions: list[BuilderActionView] = field(default_factory=list)
    contextual_actions: list[BuilderActionView] = field(default_factory=list)
    disabled_action_count: int = 0
    explanation: str | None = None


def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
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


def _action(action_id: str, label: str, action_kind: str, enabled: bool, *, reason_disabled: str | None = None, destructive: bool = False, requires_confirmation: bool = False) -> BuilderActionView:
    return BuilderActionView(
        action_id=action_id,
        label=label,
        action_kind=action_kind,
        enabled=enabled,
        reason_disabled=reason_disabled,
        destructive=destructive,
        requires_confirmation=requires_confirmation,
    )


def read_builder_action_schema(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    storage_view: StoragePanelViewModel | None = None,
    validation_view: ValidationPanelViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
    designer_view: DesignerPanelViewModel | None = None,
    explanation: str | None = None,
) -> BuilderActionSchemaView:
    source = _unwrap(source)
    source_role = _storage_role(source)

    execution_status = execution_view.execution_status if execution_view is not None else "unknown"
    validation_status = validation_view.overall_status if validation_view is not None else "unknown"
    commit_eligible = designer_view.approval_state.commit_eligible if designer_view is not None else False
    review_ready = validation_status not in {"blocked", "unknown"}
    can_run = source_role in {"working_save", "commit_snapshot"} and execution_status not in {"running", "queued"} and validation_status != "blocked"
    has_execution_record = False
    if storage_view is not None and storage_view.execution_record_card is not None and storage_view.execution_record_card.run_id is not None:
        has_execution_record = True
    elif isinstance(source, ExecutionRecordModel):
        has_execution_record = True

    primary_actions = [
        _action(
            "save_working_save",
            "Save Draft",
            "storage",
            source_role == "working_save",
            reason_disabled=None if source_role == "working_save" else "Only working saves can be saved as drafts.",
        ),
        _action(
            "review_draft",
            "Review Draft",
            "review",
            source_role == "working_save" and review_ready and execution_status not in {"running", "queued"},
            reason_disabled=(
                None
                if source_role == "working_save" and review_ready and execution_status not in {"running", "queued"}
                else "Draft review requires a working save with non-blocking validation and no active run."
            ),
        ),
        _action(
            "commit_snapshot",
            "Commit Snapshot",
            "approval",
            source_role == "working_save" and review_ready and execution_status not in {"running", "queued"} and (designer_view is None or commit_eligible),
            reason_disabled=(
                None
                if source_role == "working_save" and review_ready and execution_status not in {"running", "queued"} and (designer_view is None or commit_eligible)
                else "Commit requires a working save, non-blocking review state, no active run, and approval eligibility when designer flow is present."
            ),
            requires_confirmation=True,
        ),
        _action(
            "run_current",
            "Run Current",
            "execution",
            can_run,
            reason_disabled=None if can_run else "Running requires a draft or commit target with no blocking validation and no active run.",
        ),
        _action(
            "cancel_run",
            "Cancel Run",
            "execution",
            execution_status in {"running", "queued"},
            reason_disabled=None if execution_status in {"running", "queued"} else "No active run is available to cancel.",
            destructive=True,
            requires_confirmation=True,
        ),
    ]

    secondary_actions = [
        _action(
            "replay_latest",
            "Replay Latest",
            "execution",
            has_execution_record,
            reason_disabled=None if has_execution_record else "Replay requires an execution record.",
        ),
        _action(
            "open_diff",
            "Open Diff",
            "comparison",
            storage_view is not None and (
                (storage_view.commit_snapshot_card is not None and storage_view.commit_snapshot_card.commit_id is not None)
                or (storage_view.execution_record_card is not None and storage_view.execution_record_card.run_id is not None)
            ),
            reason_disabled=(
                None
                if storage_view is not None and (
                    (storage_view.commit_snapshot_card is not None and storage_view.commit_snapshot_card.commit_id is not None)
                    or (storage_view.execution_record_card is not None and storage_view.execution_record_card.run_id is not None)
                )
                else "Diff requires a comparison target such as a commit snapshot or execution record."
            ),
        ),
    ]

    contextual_actions: list[BuilderActionView] = []
    if designer_view is not None:
        contextual_actions.extend(
            [
                _action(
                    "approve_for_commit",
                    "Approve Proposal",
                    "designer",
                    designer_view.approval_state.commit_eligible,
                    reason_disabled=None if designer_view.approval_state.commit_eligible else "Designer proposal is not yet eligible for commit.",
                    requires_confirmation=True,
                ),
                _action(
                    "request_revision",
                    "Request Revision",
                    "designer",
                    designer_view.request_state.request_status in {"submitted", "editing"} or designer_view.intent_state.intent_id is not None,
                    reason_disabled=None if (designer_view.request_state.request_status in {"submitted", "editing"} or designer_view.intent_state.intent_id is not None) else "No active designer proposal is available for revision.",
                ),
            ]
        )

    all_actions = primary_actions + secondary_actions + contextual_actions
    return BuilderActionSchemaView(
        source_role=source_role,
        primary_actions=primary_actions,
        secondary_actions=secondary_actions,
        contextual_actions=contextual_actions,
        disabled_action_count=sum(1 for action in all_actions if not action.enabled),
        explanation=explanation,
    )


__all__ = [
    "BuilderActionView",
    "BuilderActionSchemaView",
    "read_builder_action_schema",
]
