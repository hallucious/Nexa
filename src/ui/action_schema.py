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
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.beginner_surface_gate import beginner_deep_surface_gate_active, gate_beginner_actions
from src.ui.beginner_milestones import return_use_ready


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


def _ui_metadata(source) -> dict[str, object]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}


def _workspace_anchor_id(source) -> str | None:
    if isinstance(source, WorkingSaveModel):
        return str(source.meta.working_save_id or "").strip() or None
    if isinstance(source, CommitSnapshotModel):
        return str(source.meta.source_working_save_id or "").strip() or None
    return None


def _return_use_ready(source) -> bool:
    return return_use_ready(source)


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


def _storage_action_view(action) -> BuilderActionView:
    return BuilderActionView(
        action_id=action.action_type,
        label=action.label,
        action_kind="storage",
        enabled=action.enabled,
        reason_disabled=action.reason_disabled,
    )


def read_builder_action_schema(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    storage_view: StoragePanelViewModel | None = None,
    validation_view: ValidationPanelViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
    designer_view: DesignerPanelViewModel | None = None,
    explanation: str | None = None,
    app_language: str | None = None,
) -> BuilderActionSchemaView:
    source = _unwrap(source)
    app_language = app_language or ui_language_from_sources(source)
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

    provider_setup_needed = bool(
        source_role == "working_save"
        and designer_view is not None
        and designer_view.template_gallery.visible
        and (designer_view.provider_setup_guidance.visible or designer_view.provider_inline_key_entry.visible)
        and not designer_view.provider_inline_key_entry.has_connected_provider
    )
    starter_templates_available = bool(
        source_role == "working_save"
        and designer_view is not None
        and designer_view.template_gallery.visible
        and designer_view.template_gallery.templates
    )

    external_input_needed = bool(
        source_role == "working_save"
        and designer_view is not None
        and designer_view.external_input_guidance.visible
        and not designer_view.external_input_guidance.has_configured_input
    )

    workspace_anchor_id = _workspace_anchor_id(source)
    return_use_ready = _return_use_ready(source)
    has_return_result_surface = bool(
        isinstance(source, ExecutionRecordModel)
        or has_execution_record
    )
    has_feedback_surface = bool(
        workspace_anchor_id is not None
        or isinstance(source, ExecutionRecordModel)
    )
    cost_visibility_ready = bool(
        execution_view is not None
        and execution_view.cost_visibility.visible
        and execution_status not in {"running", "queued"}
    )
    waiting_feedback_ready = bool(
        execution_view is not None
        and execution_view.waiting_feedback.visible
    )

    beginner_preunlock = beginner_deep_surface_gate_active(source)

    working_primary_actions = [
        _action(
            "save_working_save",
            ui_text("builder.action.save_working_save", app_language=app_language),
            "storage",
            source_role == "working_save",
            reason_disabled=None if source_role == "working_save" else ui_text("builder.reason.only_working_save", app_language=app_language),
        ),
        _action(
            "review_draft",
            ui_text("builder.action.review_draft", app_language=app_language),
            "review",
            source_role == "working_save" and review_ready and execution_status not in {"running", "queued"},
            reason_disabled=(
                None
                if source_role == "working_save" and review_ready and execution_status not in {"running", "queued"}
                else ui_text("builder.reason.review_requires_ready_working_save", app_language=app_language)
            ),
        ),
        _action(
            "commit_snapshot",
            ui_text("builder.action.commit_snapshot", app_language=app_language),
            "approval",
            source_role == "working_save" and review_ready and execution_status not in {"running", "queued"} and (designer_view is None or commit_eligible),
            reason_disabled=(
                None
                if source_role == "working_save" and review_ready and execution_status not in {"running", "queued"} and (designer_view is None or commit_eligible)
                else ui_text("builder.reason.commit_requires_ready_state", app_language=app_language)
            ),
            requires_confirmation=True,
        ),
        _action(
            "run_current",
            ui_text("builder.action.run_current", app_language=app_language),
            "execution",
            can_run,
            reason_disabled=None if can_run else ui_text("builder.reason.run_requires_runnable_target", app_language=app_language),
        ),
        _action(
            "cancel_run",
            ui_text("builder.action.cancel_run", app_language=app_language),
            "execution",
            execution_status in {"running", "queued"},
            reason_disabled=None if execution_status in {"running", "queued"} else ui_text("builder.reason.no_active_run_to_cancel", app_language=app_language),
            destructive=True,
            requires_confirmation=True,
        ),
    ]

    graph_navigation_available = isinstance(source, (WorkingSaveModel, CommitSnapshotModel))
    runtime_navigation_available = execution_view is not None

    deep_secondary_actions = [
        _action(
            "replay_latest",
            ui_text("builder.action.replay_latest", app_language=app_language),
            "execution",
            has_execution_record,
            reason_disabled=None if has_execution_record else ui_text("builder.reason.replay_requires_execution_record", app_language=app_language),
        ),
        _action(
            "open_diff",
            ui_text("builder.action.open_diff", app_language=app_language),
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
                else ui_text("builder.reason.diff_requires_comparison_target", app_language=app_language)
            ),
        ),
    ]

    generic_secondary_actions = (
        deep_secondary_actions
        if beginner_preunlock
        else [
            _action(
                "open_visual_editor",
                ui_text("builder.action.open_visual_editor", app_language=app_language),
                "workspace_navigation",
                graph_navigation_available,
                reason_disabled=None if graph_navigation_available else ui_text("builder.reason.visual_editor_requires_graph", app_language=app_language),
            ),
            _action(
                "open_node_configuration",
                ui_text("builder.action.open_node_configuration", app_language=app_language),
                "workspace_navigation",
                graph_navigation_available,
                reason_disabled=None if graph_navigation_available else ui_text("builder.reason.configuration_requires_graph", app_language=app_language),
            ),
            _action(
                "open_runtime_monitoring",
                ui_text("builder.action.open_runtime_monitoring", app_language=app_language),
                "workspace_navigation",
                runtime_navigation_available,
                reason_disabled=None if runtime_navigation_available else ui_text("builder.reason.runtime_monitoring_requires_execution", app_language=app_language),
            ),
            *deep_secondary_actions,
        ]
    )

    primary_actions = list(working_primary_actions)
    secondary_actions = list(generic_secondary_actions)

    if source_role == "commit_snapshot" and storage_view is not None:
        primary_actions = [
            _storage_action_view(action)
            for action in storage_view.available_actions
            if action.action_type in {"open_latest_commit", "run_from_commit", "select_rollback_target"}
        ]
        secondary_actions = [
            _storage_action_view(action)
            for action in storage_view.available_actions
            if action.action_type not in {"open_latest_commit", "run_from_commit", "select_rollback_target"}
        ] + generic_secondary_actions
    elif source_role == "execution_record" and storage_view is not None:
        primary_actions = [
            _storage_action_view(action)
            for action in storage_view.available_actions
            if action.action_type in {"open_latest_run", "open_trace", "open_artifacts", "compare_runs"}
        ]
        secondary_actions = [
            _storage_action_view(action)
            for action in storage_view.available_actions
            if action.action_type not in {"open_latest_run", "open_trace", "open_artifacts", "compare_runs"}
        ] + [
            _action(
                "replay_latest",
                ui_text("builder.action.replay_latest", app_language=app_language),
                "execution",
                has_execution_record,
                reason_disabled=None if has_execution_record else ui_text("builder.reason.replay_requires_execution_record", app_language=app_language),
            )
        ]

    contextual_actions: list[BuilderActionView] = []
    if provider_setup_needed:
        contextual_actions.append(
            _action(
                "open_provider_setup",
                ui_text("builder.action.open_provider_setup", app_language=app_language),
                "provider_setup",
                True,
            )
        )
    if starter_templates_available:
        contextual_actions.append(
            _action(
                "create_circuit_from_template",
                ui_text("builder.action.create_circuit_from_template", app_language=app_language),
                "template_gallery",
                True,
            )
        )
    if external_input_needed:
        contextual_actions.extend([
            _action(
                "open_file_input",
                ui_text("builder.action.open_file_input", app_language=app_language),
                "external_input",
                True,
            ),
            _action(
                "enter_url_input",
                ui_text("builder.action.enter_url_input", app_language=app_language),
                "external_input",
                True,
            ),
        ])

    if designer_view is not None:
        contextual_actions.extend(
            [
                _action(
                    "approve_for_commit",
                    ui_text("builder.action.approve_for_commit", app_language=app_language),
                    "designer",
                    designer_view.approval_state.commit_eligible,
                    reason_disabled=None if designer_view.approval_state.commit_eligible else ui_text("builder.reason.designer_not_commit_eligible", app_language=app_language),
                    requires_confirmation=True,
                ),
                _action(
                    "request_revision",
                    ui_text("builder.action.request_revision", app_language=app_language),
                    "designer",
                    designer_view.request_state.request_status in {"submitted", "editing"} or designer_view.intent_state.intent_id is not None,
                    reason_disabled=None if (designer_view.request_state.request_status in {"submitted", "editing"} or designer_view.intent_state.intent_id is not None) else ui_text("builder.reason.no_active_designer_proposal", app_language=app_language),
                ),
            ]
        )

    if cost_visibility_ready:
        contextual_actions.append(
            _action(
                "review_run_cost",
                ui_text("builder.action.review_run_cost", app_language=app_language),
                "execution_cost",
                True,
            )
        )

    if waiting_feedback_ready:
        contextual_actions.append(
            _action(
                "watch_run_progress",
                execution_view.waiting_feedback.next_action_label or ui_text("builder.action.watch_run_progress", app_language=app_language),
                "execution_monitoring",
                True,
            )
        )

    if return_use_ready:
        contextual_actions.extend(
            [
                _action(
                    "open_circuit_library",
                    ui_text("builder.action.open_circuit_library", app_language=app_language),
                    "return_use",
                    workspace_anchor_id is not None,
                    reason_disabled=None if workspace_anchor_id is not None else ui_text("builder.reason.library_requires_workspace", app_language=app_language),
                ),
                _action(
                    "open_result_history",
                    ui_text("builder.action.open_result_history", app_language=app_language),
                    "return_use",
                    has_return_result_surface,
                    reason_disabled=None if has_return_result_surface else ui_text("builder.reason.result_history_requires_run", app_language=app_language),
                ),
                _action(
                    "open_feedback_channel",
                    ui_text("builder.action.open_feedback_channel", app_language=app_language),
                    "return_use",
                    has_feedback_surface,
                    reason_disabled=None if has_feedback_surface else ui_text("builder.reason.feedback_requires_workspace", app_language=app_language),
                ),
            ]
        )

    primary_actions = gate_beginner_actions(primary_actions, source)
    secondary_actions = gate_beginner_actions(secondary_actions, source)
    contextual_actions = gate_beginner_actions(contextual_actions, source)

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
