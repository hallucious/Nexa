from __future__ import annotations

from dataclasses import dataclass, field, replace

from src.contracts.nex_contract import ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.inspector_panel import SelectedObjectViewModel, read_selected_object_view_model
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class ConfigurationSelectionSummaryView:
    selected_ref: str | None = None
    object_type: str = "none"
    editable_field_count: int = 0
    readonly_field_count: int = 0
    warning_count: int = 0
    constraint_count: int = 0
    preview_change_count: int = 0
    finding_count: int = 0
    editability: str = "unknown"
    has_execution_context: bool = False


@dataclass(frozen=True)
class ConfigurationReviewStateView:
    validation_status: str = "unknown"
    blocking_count: int = 0
    warning_count: int = 0
    confirmation_count: int = 0
    designer_session_mode: str = "idle"
    approval_stage: str | None = None
    commit_eligible: bool = False


@dataclass(frozen=True)
class ConfigurationReadinessView:
    posture: str = "unknown"
    posture_label: str | None = None
    selected_object_type: str = "none"
    editable_field_count: int = 0
    readonly_field_count: int = 0
    preview_change_count: int = 0
    constraint_count: int = 0
    blocking_count: int = 0
    warning_count: int = 0
    execution_locked: bool = False
    review_ready: bool = False
    has_execution_context: bool = False
    enabled_local_action_count: int = 0


@dataclass(frozen=True)
class ConfigurationFocusHintView:
    hint_kind: str = "none"
    target_ref: str | None = None
    label: str | None = None
    explanation: str | None = None
    suggested_action_id: str | None = None


@dataclass(frozen=True)
class ConfigurationWorkspaceHandoffView:
    destination_workspace: str = "node_configuration"
    destination_panel: str | None = "inspector"
    target_ref: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ConfigurationActionShortcutView:
    action: BuilderActionView
    target_ref: str | None = None
    priority: str = "secondary"
    emphasis: str = "neutral"
    explanation: str | None = None


@dataclass(frozen=True)
class ConfigurationAttentionTargetView:
    attention_kind: str = "general"
    urgency: str = "low"
    target_ref: str | None = None
    title: str | None = None
    summary: str | None = None
    destination_workspace: str = "node_configuration"
    destination_panel: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    blocking: bool = False


@dataclass(frozen=True)
class ConfigurationProgressStageView:
    stage_id: str = "select"
    label: str | None = None
    state: str = "blocked"
    state_label: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    target_ref: str | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class ConfigurationClosureBarrierView:
    barrier_kind: str = "general"
    severity: str = "medium"
    target_ref: str | None = None
    title: str | None = None
    summary: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    destination_workspace: str = "node_configuration"
    destination_panel: str | None = None
    blocking: bool = False


@dataclass(frozen=True)
class ConfigurationClosureVerdictView:
    closure_state: str = "hold_node_configuration"
    closure_label: str | None = None
    should_move_on: bool = False
    move_on_target_workspace: str | None = None
    pending_barrier_count: int = 0
    blocking_barrier_count: int = 0
    dominant_barrier_kind: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class NodeConfigurationWorkspaceViewModel:
    workspace_status: str = "ready"
    workspace_status_label: str | None = None
    storage_role: str = "none"
    inspector: SelectedObjectViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    designer: DesignerPanelViewModel | None = None
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    selection_summary: ConfigurationSelectionSummaryView = field(default_factory=ConfigurationSelectionSummaryView)
    review_state: ConfigurationReviewStateView = field(default_factory=ConfigurationReviewStateView)
    readiness: ConfigurationReadinessView = field(default_factory=ConfigurationReadinessView)
    focus_hint: ConfigurationFocusHintView = field(default_factory=ConfigurationFocusHintView)
    workspace_handoff: ConfigurationWorkspaceHandoffView = field(default_factory=ConfigurationWorkspaceHandoffView)
    can_edit_configuration: bool = False
    can_submit_designer_request: bool = False
    can_commit_configuration: bool = False
    local_actions: list[BuilderActionView] = field(default_factory=list)
    action_shortcuts: list[ConfigurationActionShortcutView] = field(default_factory=list)
    attention_targets: list[ConfigurationAttentionTargetView] = field(default_factory=list)
    progress_stages: list[ConfigurationProgressStageView] = field(default_factory=list)
    closure_barriers: list[ConfigurationClosureBarrierView] = field(default_factory=list)
    closure_verdict: ConfigurationClosureVerdictView = field(default_factory=ConfigurationClosureVerdictView)
    explanation: str | None = None
    suggested_actions: list[BuilderActionView] = field(default_factory=list)


_ACTION_META: dict[str, tuple[str, str, str]] = {
    "open_visual_editor": ("builder.action.open_visual_editor", "Open editor", "workspace_navigation"),
    "open_runtime_monitoring": ("builder.action.open_runtime_monitoring", "Open runtime monitoring", "workspace_navigation"),
    "review_draft": ("builder.action.review_draft", "Review draft", "review"),
    "commit_snapshot": ("builder.action.commit_snapshot", "Commit snapshot", "approval"),
    "request_revision": ("builder.action.request_revision", "Request revision", "designer"),
    "open_diff": ("builder.action.open_diff", "Open diff", "comparison"),
    "replay_latest": ("builder.action.replay_latest", "Replay latest", "execution"),
    "run_current": ("builder.action.run_current", "Run current", "execution"),
    "save_working_save": ("builder.action.save_working_save", "Save draft", "storage"),
    "open_file_input": ("builder.action.open_file_input", "Use a file", "external_input"),
}


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



def _workspace_explanation(
    *,
    workspace_status: str,
    app_language: str,
    validation_vm: ValidationPanelViewModel | None,
    designer_vm: DesignerPanelViewModel | None,
) -> str | None:
    if workspace_status == "awaiting_selection":
        return ui_text("workspace.configuration.explanation.awaiting_selection", app_language=app_language)
    if workspace_status == "blocked":
        if validation_vm is not None and validation_vm.beginner_summary.cause:
            return validation_vm.beginner_summary.cause
        return ui_text("workspace.configuration.explanation.blocked", app_language=app_language)
    if workspace_status == "designer_review":
        if designer_vm is not None and designer_vm.preview_state.one_sentence_summary:
            return designer_vm.preview_state.one_sentence_summary
        return ui_text("workspace.configuration.explanation.designer_review", app_language=app_language)
    if workspace_status == "run_review":
        return ui_text("workspace.configuration.explanation.run_review", app_language=app_language)
    return ui_text("workspace.configuration.explanation.configuring", app_language=app_language, fallback_text=None)



def _action_lookup(action_schema: BuilderActionSchemaView) -> dict[str, BuilderActionView]:
    return {
        action.action_id: action
        for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    }



def _scoped_action(action: BuilderActionView) -> BuilderActionView:
    return replace(action, target_scope="node_configuration")



def _manual_action(
    action_id: str,
    *,
    app_language: str,
    enabled: bool,
    reason_disabled: str | None = None,
) -> BuilderActionView:
    text_key, fallback_text, action_kind = _ACTION_META[action_id]
    return BuilderActionView(
        action_id=action_id,
        label=ui_text(text_key, app_language=app_language, fallback_text=fallback_text),
        action_kind=action_kind,
        enabled=enabled,
        reason_disabled=reason_disabled,
        target_scope="node_configuration",
    )



def _unique_actions(actions: list[BuilderActionView | None]) -> list[BuilderActionView]:
    deduped: list[BuilderActionView] = []
    seen: set[str] = set()
    for action in actions:
        if action is None or action.action_id in seen:
            continue
        seen.add(action.action_id)
        deduped.append(action)
    return deduped



def _action_or_manual(
    action_map: dict[str, BuilderActionView],
    action_id: str,
    *,
    app_language: str,
    enabled: bool = True,
    reason_disabled: str | None = None,
) -> BuilderActionView | None:
    action = action_map.get(action_id)
    if action is not None:
        return _scoped_action(action)
    if action_id in _ACTION_META:
        return _manual_action(action_id, app_language=app_language, enabled=enabled, reason_disabled=reason_disabled)
    return None



def _workspace_local_actions(
    *,
    workspace_status: str,
    app_language: str,
    action_schema: BuilderActionSchemaView,
    selection_summary: ConfigurationSelectionSummaryView,
    review_state: ConfigurationReviewStateView,
) -> list[BuilderActionView]:
    action_map = _action_lookup(action_schema)
    runtime_reason = None if selection_summary.has_execution_context else ui_text(
        "builder.reason.runtime_monitoring_requires_execution",
        app_language=app_language,
    )
    diff_action = _action_or_manual(action_map, "open_diff", app_language=app_language)

    if workspace_status == "awaiting_selection":
        return _unique_actions([
            _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
            _action_or_manual(action_map, "save_working_save", app_language=app_language),
            _action_or_manual(action_map, "open_file_input", app_language=app_language),
        ])

    if workspace_status == "blocked":
        return _unique_actions([
            _action_or_manual(action_map, "request_revision", app_language=app_language),
            diff_action,
            _action_or_manual(
                action_map,
                "open_runtime_monitoring",
                app_language=app_language,
                enabled=selection_summary.has_execution_context,
                reason_disabled=runtime_reason,
            ) if selection_summary.has_execution_context else None,
            _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
        ])

    if workspace_status == "designer_review":
        return _unique_actions([
            _action_or_manual(action_map, "review_draft", app_language=app_language),
            _action_or_manual(action_map, "commit_snapshot", app_language=app_language),
            _action_or_manual(action_map, "request_revision", app_language=app_language),
            diff_action,
        ])

    if workspace_status == "run_review":
        return _unique_actions([
            _action_or_manual(
                action_map,
                "open_runtime_monitoring",
                app_language=app_language,
                enabled=selection_summary.has_execution_context,
                reason_disabled=runtime_reason,
            ),
            _action_or_manual(action_map, "replay_latest", app_language=app_language),
            _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
        ])

    can_review = any(a.action_id in {"review_draft", "commit_snapshot", "approve_for_commit"} and a.enabled for a in action_map.values())
    can_run = any(a.action_id in {"run_current", "run_from_commit"} and a.enabled for a in action_map.values())

    return _unique_actions([
        _action_or_manual(action_map, "review_draft", app_language=app_language) if can_review else None,
        _action_or_manual(action_map, "run_current", app_language=app_language) if can_run else None,
        _action_or_manual(
            action_map,
            "open_runtime_monitoring",
            app_language=app_language,
            enabled=selection_summary.has_execution_context,
            reason_disabled=runtime_reason,
        ) if selection_summary.has_execution_context else None,
        _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
    ])



def _workspace_suggested_actions(*, workspace_status: str, local_actions: list[BuilderActionView]) -> list[BuilderActionView]:
    if workspace_status in {"awaiting_selection", "blocked", "designer_review", "run_review", "configuring"}:
        return local_actions[:3]
    return local_actions[:2]



def _readiness_posture(*, workspace_status: str, selection_summary: ConfigurationSelectionSummaryView) -> str:
    if workspace_status == "awaiting_selection":
        return "select_target"
    if workspace_status == "blocked":
        return "repair_selection"
    if workspace_status == "designer_review":
        return "review_configuration"
    if workspace_status == "run_review":
        return "run_readonly"
    if selection_summary.editability == "execution_locked":
        return "execution_locked"
    if selection_summary.editability == "editable":
        return "edit_configuration"
    return "inspect_configuration"



def _configuration_readiness(
    *,
    workspace_status: str,
    selection_summary: ConfigurationSelectionSummaryView,
    review_state: ConfigurationReviewStateView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> ConfigurationReadinessView:
    posture = _readiness_posture(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
    )
    review_ready = any(action.action_id in {"review_draft", "commit_snapshot", "approve_for_commit"} and action.enabled for action in local_actions)
    return ConfigurationReadinessView(
        posture=posture,
        posture_label=ui_text(
            f"workspace.configuration.readiness.{posture}",
            app_language=app_language,
            fallback_text=posture.replace("_", " "),
        ),
        selected_object_type=selection_summary.object_type,
        editable_field_count=selection_summary.editable_field_count,
        readonly_field_count=selection_summary.readonly_field_count,
        preview_change_count=selection_summary.preview_change_count,
        constraint_count=selection_summary.constraint_count,
        blocking_count=review_state.blocking_count,
        warning_count=review_state.warning_count,
        execution_locked=selection_summary.editability == "execution_locked",
        review_ready=review_ready,
        has_execution_context=selection_summary.has_execution_context,
        enabled_local_action_count=sum(1 for action in local_actions if action.enabled),
    )



def _action_label(action: BuilderActionView | None, *, app_language: str) -> str | None:
    if action is None:
        return None
    return action.label or ui_text(
        f"builder.action.{action.action_id}",
        app_language=app_language,
        fallback_text=action.action_id.replace("_", " "),
    )



def _configuration_focus_hint(
    *,
    workspace_status: str,
    inspector_vm: SelectedObjectViewModel | None,
    selection_summary: ConfigurationSelectionSummaryView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> ConfigurationFocusHintView:
    primary_action = local_actions[0] if local_actions else None
    target_ref = selection_summary.selected_ref
    label = inspector_vm.title if inspector_vm is not None else None

    if workspace_status == "awaiting_selection":
        editor_action = next((a for a in local_actions if a.action_id == "open_visual_editor"), primary_action)
        return ConfigurationFocusHintView(
            hint_kind="awaiting_selection",
            explanation=ui_text(
                "workspace.configuration.focus.awaiting_selection",
                app_language=app_language,
                fallback_text="Return to the visual editor and choose the step or connection you want to configure.",
            ),
            suggested_action_id=editor_action.action_id if editor_action is not None else None,
        )

    if workspace_status == "blocked":
        revision_action = next((a for a in local_actions if a.action_id == "request_revision"), primary_action)
        return ConfigurationFocusHintView(
            hint_kind="repair_selection",
            target_ref=target_ref,
            label=label,
            explanation=ui_text(
                "workspace.configuration.focus.blocked",
                app_language=app_language,
                fallback_text="{label} is blocked. Review the findings and repair this configuration before continuing.",
                label=label or ui_text("workspace.node_configuration.name.beginner", app_language=app_language, fallback_text="step settings"),
            ),
            suggested_action_id=revision_action.action_id if revision_action is not None else None,
        )

    if workspace_status == "designer_review":
        review_action = next((a for a in local_actions if a.action_id in {"commit_snapshot", "review_draft", "request_revision"}), primary_action)
        return ConfigurationFocusHintView(
            hint_kind="designer_review",
            target_ref=target_ref,
            label=label,
            explanation=ui_text(
                "workspace.configuration.focus.designer_review",
                app_language=app_language,
                fallback_text="{label} has pending proposed changes. Review them here before saving or requesting another revision.",
                label=label or ui_text("workspace.node_configuration.name.beginner", app_language=app_language, fallback_text="step settings"),
            ),
            suggested_action_id=review_action.action_id if review_action is not None else None,
        )

    if workspace_status == "run_review":
        runtime_action = next((a for a in local_actions if a.action_id in {"open_runtime_monitoring", "replay_latest"}), primary_action)
        return ConfigurationFocusHintView(
            hint_kind="run_review",
            target_ref=target_ref,
            label=label,
            explanation=ui_text(
                "workspace.configuration.focus.run_review",
                app_language=app_language,
                fallback_text="{label} is tied to an execution result. Treat these fields as read-only and inspect runtime evidence next.",
                label=label or ui_text("workspace.node_configuration.name.beginner", app_language=app_language, fallback_text="step settings"),
            ),
            suggested_action_id=runtime_action.action_id if runtime_action is not None else None,
        )

    next_action = next((a for a in local_actions if a.action_id in {"review_draft", "run_current", "open_visual_editor"}), primary_action)
    return ConfigurationFocusHintView(
        hint_kind="edit_selection",
        target_ref=target_ref,
        label=label,
        explanation=ui_text(
            "workspace.configuration.focus.configuring",
            app_language=app_language,
            fallback_text="Inspect {label}, update the editable fields here, then move to review or run when ready.",
            label=label or ui_text("workspace.node_configuration.name.beginner", app_language=app_language, fallback_text="step settings"),
        ),
        suggested_action_id=next_action.action_id if next_action is not None else None,
    )



def _configuration_handoff(
    *,
    workspace_status: str,
    selection_summary: ConfigurationSelectionSummaryView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> ConfigurationWorkspaceHandoffView:
    def _first_action(*action_ids: str) -> BuilderActionView | None:
        for action_id in action_ids:
            action = next((item for item in local_actions if item.action_id == action_id), None)
            if action is not None:
                return action
        return local_actions[0] if local_actions else None

    if workspace_status == "awaiting_selection":
        action = _first_action("open_visual_editor")
        return ConfigurationWorkspaceHandoffView(
            destination_workspace="visual_editor",
            destination_panel="graph",
            action_id=action.action_id if action is not None else None,
            action_label=_action_label(action, app_language=app_language),
            reason=ui_text(
                "workspace.configuration.handoff.awaiting_selection",
                app_language=app_language,
                fallback_text="Go back to the visual editor and pick the exact object you want to configure.",
            ),
        )

    if workspace_status == "blocked":
        action = _first_action("request_revision", "open_diff")
        return ConfigurationWorkspaceHandoffView(
            destination_workspace="node_configuration",
            destination_panel="validation",
            target_ref=selection_summary.selected_ref,
            action_id=action.action_id if action is not None else None,
            action_label=_action_label(action, app_language=app_language),
            reason=ui_text(
                "workspace.configuration.handoff.blocked",
                app_language=app_language,
                fallback_text="Stay in node configuration, inspect validation, and repair the blocked selection before moving on.",
            ),
        )

    if workspace_status == "designer_review":
        action = _first_action("commit_snapshot", "review_draft", "request_revision")
        return ConfigurationWorkspaceHandoffView(
            destination_workspace="node_configuration",
            destination_panel="designer",
            target_ref=selection_summary.selected_ref,
            action_id=action.action_id if action is not None else None,
            action_label=_action_label(action, app_language=app_language),
            reason=ui_text(
                "workspace.configuration.handoff.designer_review",
                app_language=app_language,
                fallback_text="Use the designer and review surfaces here to decide whether to save, revise, or keep editing this configuration.",
            ),
        )

    if workspace_status == "run_review":
        action = _first_action("open_runtime_monitoring", "replay_latest")
        return ConfigurationWorkspaceHandoffView(
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            target_ref=selection_summary.selected_ref,
            action_id=action.action_id if action is not None else None,
            action_label=_action_label(action, app_language=app_language),
            reason=ui_text(
                "workspace.configuration.handoff.run_review",
                app_language=app_language,
                fallback_text="This selection is in a run-related posture. Open runtime monitoring to inspect the execution evidence behind it.",
            ),
        )

    action = _first_action("review_draft", "run_current", "open_visual_editor")
    return ConfigurationWorkspaceHandoffView(
        destination_workspace="node_configuration",
        destination_panel="inspector",
        target_ref=selection_summary.selected_ref,
        action_id=action.action_id if action is not None else None,
        action_label=_action_label(action, app_language=app_language),
        reason=ui_text(
            "workspace.configuration.handoff.configuring",
            app_language=app_language,
            fallback_text="Stay in node configuration while you refine the current selection, then move to review or run when ready.",
        ),
    )



def _shortcut_explanation_key(action_id: str) -> str:
    mapping = {
        "open_visual_editor": "workspace.configuration.shortcut.choose_target",
        "request_revision": "workspace.configuration.shortcut.repair_selection",
        "open_diff": "workspace.configuration.shortcut.review_diff",
        "review_draft": "workspace.configuration.shortcut.review_configuration",
        "commit_snapshot": "workspace.configuration.shortcut.commit_configuration",
        "replay_latest": "workspace.configuration.shortcut.replay_latest",
        "open_runtime_monitoring": "workspace.configuration.shortcut.inspect_runtime",
        "run_current": "workspace.configuration.shortcut.run_current",
        "save_working_save": "workspace.configuration.shortcut.save_draft",
        "open_file_input": "workspace.configuration.shortcut.add_input",
    }
    return mapping.get(action_id, "workspace.configuration.shortcut.default")



def _configuration_action_shortcuts(
    *,
    workspace_status: str,
    selection_summary: ConfigurationSelectionSummaryView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> list[ConfigurationActionShortcutView]:
    priority_specs: list[tuple[str, str, str]]
    if workspace_status == "awaiting_selection":
        priority_specs = [
            ("open_visual_editor", "primary", "selection"),
            ("save_working_save", "secondary", "storage"),
            ("open_file_input", "secondary", "input"),
        ]
    elif workspace_status == "blocked":
        priority_specs = [
            ("request_revision", "primary", "repair"),
            ("open_diff", "secondary", "review"),
            ("open_runtime_monitoring", "secondary", "runtime"),
            ("open_visual_editor", "secondary", "selection"),
        ]
    elif workspace_status == "designer_review":
        priority_specs = [
            ("review_draft", "primary", "review"),
            ("commit_snapshot", "secondary", "approval"),
            ("request_revision", "secondary", "repair"),
            ("open_diff", "secondary", "comparison"),
        ]
    elif workspace_status == "run_review":
        priority_specs = [
            ("open_runtime_monitoring", "primary", "runtime"),
            ("replay_latest", "secondary", "runtime"),
            ("open_visual_editor", "secondary", "navigation"),
        ]
    else:
        priority_specs = [
            ("review_draft", "primary", "review"),
            ("run_current", "secondary", "run"),
            ("open_runtime_monitoring", "secondary", "runtime"),
            ("open_visual_editor", "secondary", "navigation"),
        ]

    action_map = {action.action_id: action for action in local_actions}
    shortcuts: list[ConfigurationActionShortcutView] = []
    for action_id, priority, emphasis in priority_specs:
        action = action_map.get(action_id)
        if action is None:
            continue
        shortcuts.append(
            ConfigurationActionShortcutView(
                action=action,
                target_ref=selection_summary.selected_ref,
                priority=priority,
                emphasis=emphasis,
                explanation=ui_text(
                    _shortcut_explanation_key(action.action_id),
                    app_language=app_language,
                    fallback_text=action.label,
                ),
            )
        )
    return shortcuts





def _configuration_attention_targets(
    *,
    workspace_status: str,
    selection_summary: ConfigurationSelectionSummaryView,
    workspace_handoff: ConfigurationWorkspaceHandoffView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> list[ConfigurationAttentionTargetView]:
    action_map = {action.action_id: action for action in local_actions}

    def attention(attention_kind: str, *, urgency: str, title_key: str, fallback_title: str, summary_key: str, fallback_summary: str, action_id: str | None, blocking: bool = False, **params) -> ConfigurationAttentionTargetView:
        action = action_map.get(action_id) if action_id is not None else None
        return ConfigurationAttentionTargetView(
            attention_kind=attention_kind,
            urgency=urgency,
            target_ref=selection_summary.selected_ref,
            title=ui_text(title_key, app_language=app_language, fallback_text=fallback_title, **params),
            summary=ui_text(summary_key, app_language=app_language, fallback_text=fallback_summary, **params),
            destination_workspace=workspace_handoff.destination_workspace,
            destination_panel=workspace_handoff.destination_panel,
            action_id=action_id,
            action_label=_action_label(action, app_language=app_language),
            blocking=blocking,
        )

    label = selection_summary.selected_ref or ui_text("workspace.node_configuration.name.beginner", app_language=app_language, fallback_text="step settings")
    if workspace_status == "awaiting_selection":
        return [attention("choose_target", urgency="medium", title_key="workspace.configuration.attention.select.title", fallback_title="Choose a target to configure", summary_key="workspace.configuration.attention.select.summary", fallback_summary="Return to the visual editor and pick the exact step or connection you want to configure.", action_id="open_visual_editor")]
    if workspace_status == "blocked":
        return [attention("repair_selection", urgency="high", title_key="workspace.configuration.attention.repair.title", fallback_title="Repair the blocked selection first", summary_key="workspace.configuration.attention.repair.summary", fallback_summary="{label} still has blocking findings. Repair it here before continuing.", action_id="request_revision", blocking=True, label=label)]
    if workspace_status == "designer_review":
        return [attention("review_pending_changes", urgency="medium", title_key="workspace.configuration.attention.review.title", fallback_title="Review the pending configuration changes", summary_key="workspace.configuration.attention.review.summary", fallback_summary="Review the proposed changes for {label} before committing or requesting another revision.", action_id="review_draft", label=label)]
    if workspace_status == "run_review":
        return [attention("inspect_runtime", urgency="high", title_key="workspace.configuration.attention.runtime.title", fallback_title="Inspect runtime evidence first", summary_key="workspace.configuration.attention.runtime.summary", fallback_summary="This configuration is linked to execution evidence. Inspect runtime monitoring before treating the review as settled.", action_id="open_runtime_monitoring")]
    return [attention("edit_selection", urgency="medium", title_key="workspace.configuration.attention.edit.title", fallback_title="Keep refining the selected configuration", summary_key="workspace.configuration.attention.edit.summary", fallback_summary="Continue editing {label}, then move into review or run when the fields look right.", action_id="review_draft" if any(a.action_id == "review_draft" for a in local_actions) else "run_current", label=label)]



def _configuration_progress_stages(
    *,
    workspace_status: str,
    selection_summary: ConfigurationSelectionSummaryView,
    review_state: ConfigurationReviewStateView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> list[ConfigurationProgressStageView]:
    action_map = {action.action_id: action for action in local_actions}
    def stage(stage_id: str, *, state: str, action_id: str | None, explanation_key: str, fallback_explanation: str) -> ConfigurationProgressStageView:
        action = action_map.get(action_id) if action_id is not None else None
        return ConfigurationProgressStageView(
            stage_id=stage_id,
            label=ui_text(f"workspace.configuration.progress.stage.{stage_id}", app_language=app_language, fallback_text=stage_id.replace("_", " ")),
            state=state,
            state_label=ui_text(f"workspace.configuration.progress.state.{state}", app_language=app_language, fallback_text=state.replace("_", " ")),
            action_id=action_id,
            action_label=_action_label(action, app_language=app_language),
            target_ref=selection_summary.selected_ref,
            explanation=ui_text(explanation_key, app_language=app_language, fallback_text=fallback_explanation),
        )
    if workspace_status == "awaiting_selection":
        return [
            stage("select", state="active", action_id="open_visual_editor", explanation_key="workspace.configuration.progress.select.awaiting", fallback_explanation="Choose the exact object you want to configure first."),
            stage("configure", state="blocked", action_id=None, explanation_key="workspace.configuration.progress.configure.awaiting", fallback_explanation="Configuration cannot start until a target is selected."),
            stage("review", state="blocked", action_id=None, explanation_key="workspace.configuration.progress.review.awaiting", fallback_explanation="Review starts after a concrete configuration target exists."),
            stage("run", state="blocked", action_id=None, explanation_key="workspace.configuration.progress.run.awaiting", fallback_explanation="Running comes after selection and configuration."),
        ]
    if workspace_status == "blocked":
        return [
            stage("select", state="completed", action_id="open_visual_editor", explanation_key="workspace.configuration.progress.select.done", fallback_explanation="A configuration target is already selected."),
            stage("configure", state="blocked", action_id="request_revision", explanation_key="workspace.configuration.progress.configure.blocked", fallback_explanation="Repair the blocked configuration before treating editing as stable."),
            stage("review", state="blocked", action_id="open_diff", explanation_key="workspace.configuration.progress.review.blocked", fallback_explanation="Review is blocked until the current selection is repaired."),
            stage("run", state="blocked", action_id="open_runtime_monitoring", explanation_key="workspace.configuration.progress.run.blocked", fallback_explanation="Execution follow-up should wait until the blocking configuration issue is repaired."),
        ]
    if workspace_status == "designer_review":
        return [
            stage("select", state="completed", action_id="open_visual_editor", explanation_key="workspace.configuration.progress.select.done", fallback_explanation="A configuration target is already selected."),
            stage("configure", state="completed", action_id="review_draft", explanation_key="workspace.configuration.progress.configure.done", fallback_explanation="Field-level configuration work is already represented in this proposal."),
            stage("review", state="active", action_id="review_draft", explanation_key="workspace.configuration.progress.review.active", fallback_explanation="Review the pending proposed changes for this selection now."),
            stage("run", state="pending", action_id="commit_snapshot", explanation_key="workspace.configuration.progress.run.pending", fallback_explanation="Running should follow after the configuration review is resolved."),
        ]
    if workspace_status == "run_review":
        return [
            stage("select", state="completed", action_id="open_visual_editor", explanation_key="workspace.configuration.progress.select.done", fallback_explanation="A configuration target is already selected."),
            stage("configure", state="completed", action_id="open_visual_editor", explanation_key="workspace.configuration.progress.configure.done", fallback_explanation="The configuration is already established for this reviewed selection."),
            stage("review", state="completed", action_id="open_runtime_monitoring", explanation_key="workspace.configuration.progress.review.done", fallback_explanation="Configuration review has already advanced into execution-linked inspection."),
            stage("run", state="active", action_id="open_runtime_monitoring", explanation_key="workspace.configuration.progress.run.active", fallback_explanation="Execution evidence is now the primary surface for this selection."),
        ]
    review_action = "review_draft" if any(a.action_id == "review_draft" and a.enabled for a in local_actions) else None
    run_action = "run_current" if any(a.action_id == "run_current" and a.enabled for a in local_actions) else None
    review_state_value = "ready" if review_action is not None else "pending"
    run_state_value = "ready" if run_action is not None and review_state.blocking_count == 0 else "pending"
    return [
        stage("select", state="completed", action_id="open_visual_editor", explanation_key="workspace.configuration.progress.select.done", fallback_explanation="A configuration target is already selected."),
        stage("configure", state="active", action_id=review_action or run_action or "open_visual_editor", explanation_key="workspace.configuration.progress.configure.active", fallback_explanation="You are actively refining the selected configuration fields now."),
        stage("review", state=review_state_value, action_id=review_action, explanation_key="workspace.configuration.progress.review.ready" if review_action else "workspace.configuration.progress.review.pending", fallback_explanation="Move into review when the current fields look right." if review_action else "Review will become available after configuration work is stable."),
        stage("run", state=run_state_value, action_id=run_action, explanation_key="workspace.configuration.progress.run.ready" if run_action else "workspace.configuration.progress.run.pending", fallback_explanation="This configuration is healthy enough to support running the workflow." if run_action else "Running should wait until review and configuration readiness are stronger."),
    ]



def _configuration_closure_barriers(
    *,
    workspace_status: str,
    selection_summary: ConfigurationSelectionSummaryView,
    workspace_handoff: ConfigurationWorkspaceHandoffView,
    attention_targets: list[ConfigurationAttentionTargetView],
    review_state: ConfigurationReviewStateView,
    local_actions: list[BuilderActionView],
    app_language: str,
) -> list[ConfigurationClosureBarrierView]:
    action_map = {action.action_id: action for action in local_actions}
    def barrier(barrier_kind: str, *, severity: str, title_key: str, fallback_title: str, summary_key: str, fallback_summary: str, action_id: str | None, destination_workspace: str, destination_panel: str | None, blocking: bool = False, **params) -> ConfigurationClosureBarrierView:
        action = action_map.get(action_id) if action_id is not None else None
        return ConfigurationClosureBarrierView(
            barrier_kind=barrier_kind,
            severity=severity,
            target_ref=selection_summary.selected_ref,
            title=ui_text(title_key, app_language=app_language, fallback_text=fallback_title, **params),
            summary=ui_text(summary_key, app_language=app_language, fallback_text=fallback_summary, **params),
            action_id=action_id,
            action_label=_action_label(action, app_language=app_language),
            destination_workspace=destination_workspace,
            destination_panel=destination_panel,
            blocking=blocking,
        )
    barriers=[]
    primary_attention = attention_targets[0] if attention_targets else None
    label = selection_summary.selected_ref or ui_text("workspace.node_configuration.name.beginner", app_language=app_language, fallback_text="step settings")
    if workspace_status == "awaiting_selection":
        return [barrier("choose_target", severity="medium", title_key="workspace.configuration.barrier.select.title", fallback_title="Choose a configuration target first", summary_key="workspace.configuration.barrier.select.summary", fallback_summary="Node configuration cannot progress until a concrete step or connection is selected.", action_id="open_visual_editor", destination_workspace="visual_editor", destination_panel="graph", blocking=True)]
    if workspace_status == "blocked":
        return [barrier("repair_blocked_configuration", severity="high", title_key="workspace.configuration.barrier.repair.title", fallback_title="Repair the blocked configuration", summary_key="workspace.configuration.barrier.repair.summary", fallback_summary="{label} still has blocking findings. Repair this configuration before treating the workspace as healthy.", action_id="request_revision", destination_workspace="node_configuration", destination_panel="validation", blocking=True, label=label)]
    if workspace_status == "designer_review":
        return [barrier("review_pending_changes", severity="medium", title_key="workspace.configuration.barrier.review.title", fallback_title="Resolve the pending configuration review", summary_key="workspace.configuration.barrier.review.summary", fallback_summary="Proposed changes for {label} still need review or revision before this workspace can be treated as settled.", action_id="review_draft", destination_workspace="node_configuration", destination_panel="designer", label=label)]
    if workspace_status == "run_review":
        return [barrier("inspect_runtime_evidence", severity="medium", title_key="workspace.configuration.barrier.runtime.title", fallback_title="Inspect runtime evidence", summary_key="workspace.configuration.barrier.runtime.summary", fallback_summary="Execution-linked evidence is still the active context for this selection. Review it in runtime monitoring before calling configuration work done.", action_id="open_runtime_monitoring", destination_workspace="runtime_monitoring", destination_panel="execution")]
    if review_state.warning_count > 0:
        barriers.append(barrier("address_warnings", severity="low", title_key="workspace.configuration.barrier.warning.title", fallback_title="Review the remaining warnings", summary_key="workspace.configuration.barrier.warning.summary", fallback_summary="Warnings remain attached to this selection. Review them before widening scope away from node configuration.", action_id=workspace_handoff.action_id, destination_workspace=workspace_handoff.destination_workspace, destination_panel=workspace_handoff.destination_panel))
    if primary_attention is not None and primary_attention.action_id is not None:
        barriers.append(barrier("follow_attention", severity="low", title_key="workspace.configuration.barrier.attention.title", fallback_title="Follow the current configuration priority", summary_key="workspace.configuration.barrier.attention.summary", fallback_summary="The current configuration priority is the cleanest path forward from this workspace state.", action_id=primary_attention.action_id, destination_workspace=primary_attention.destination_workspace, destination_panel=primary_attention.destination_panel, blocking=primary_attention.blocking))
    return barriers[:2]



def _configuration_closure_verdict(*, workspace_status: str, selection_summary: ConfigurationSelectionSummaryView, closure_barriers: list[ConfigurationClosureBarrierView], app_language: str) -> ConfigurationClosureVerdictView:
    pending_barrier_count = len(closure_barriers)
    blocking_barrier_count = sum(1 for barrier in closure_barriers if barrier.blocking)
    dominant_barrier = closure_barriers[0] if closure_barriers else None
    dominant_barrier_kind = dominant_barrier.barrier_kind if dominant_barrier is not None else None
    if workspace_status == "awaiting_selection":
        closure_state = "hold_node_configuration"; should_move_on=False; move_on_target=None
        summary_key="workspace.configuration.closure.hold_selection"; fallback_summary="Node configuration still needs a real target before this sector can be considered healthy."
    elif workspace_status == "blocked" or blocking_barrier_count > 0:
        closure_state = "hold_node_configuration"; should_move_on=False; move_on_target=None
        summary_key="workspace.configuration.closure.hold_blocked"; fallback_summary="Blocking configuration issues still need repair before moving on from this workspace sector."
    elif workspace_status == "designer_review":
        closure_state = "hold_node_configuration"; should_move_on=False; move_on_target=None
        summary_key="workspace.configuration.closure.hold_review"; fallback_summary="Configuration review is still active here. Resolve it before moving on to the next workspace sector."
    elif workspace_status in {"run_review", "configuring"} and selection_summary.object_type not in {"none", "unknown"}:
        closure_state = "ready_to_move_on"; should_move_on=True; move_on_target="runtime_monitoring"
        summary_key="workspace.configuration.closure.ready_to_move_on"; fallback_summary="Node configuration is locally healthy enough. Re-evaluate runtime monitoring next unless new cross-workspace evidence reopens this sector."
    else:
        closure_state = "near_closed"; should_move_on=False; move_on_target=None
        summary_key="workspace.configuration.closure.near_closed"; fallback_summary="Node configuration is close to closure, but it still needs one more local pass before moving on."
    return ConfigurationClosureVerdictView(
        closure_state=closure_state,
        closure_label=ui_text(f"workspace.configuration.closure.state.{closure_state}", app_language=app_language, fallback_text=closure_state.replace("_", " ")),
        should_move_on=should_move_on,
        move_on_target_workspace=move_on_target,
        pending_barrier_count=pending_barrier_count,
        blocking_barrier_count=blocking_barrier_count,
        dominant_barrier_kind=dominant_barrier_kind,
        summary=ui_text(summary_key, app_language=app_language, fallback_text=fallback_summary),
    )


def read_node_configuration_workspace_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    selected_ref: str | None = None,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> NodeConfigurationWorkspaceViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    inspector_vm = read_selected_object_view_model(
        source_unwrapped,
        selected_ref=selected_ref,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
    ) if source_unwrapped is not None else None
    validation_vm = read_validation_panel_view_model(
        source_unwrapped,
        validation_report=validation_report,
        precheck=precheck,
        execution_record=execution_record,
    ) if source_unwrapped is not None else None
    designer_vm = read_designer_panel_view_model(
        source_unwrapped,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if source_unwrapped is not None else None
    coordination_vm = read_panel_coordination_state(
        source_unwrapped,
        validation_view=validation_vm,
        designer_view=designer_vm,
    )
    action_schema = read_builder_action_schema(
        source_unwrapped,
        validation_view=validation_vm,
        designer_view=designer_vm,
    )

    selection_summary = ConfigurationSelectionSummaryView(
        selected_ref=(f"{inspector_vm.object_type}:{inspector_vm.object_id}" if inspector_vm is not None and inspector_vm.object_id is not None else selected_ref),
        object_type=inspector_vm.object_type if inspector_vm is not None else "none",
        editable_field_count=len(inspector_vm.editable_fields) if inspector_vm is not None else 0,
        readonly_field_count=len(inspector_vm.readonly_fields) if inspector_vm is not None else 0,
        warning_count=len(inspector_vm.warnings) if inspector_vm is not None else 0,
        constraint_count=len(inspector_vm.constraints) if inspector_vm is not None else 0,
        preview_change_count=len(inspector_vm.related_preview_changes) if inspector_vm is not None else 0,
        finding_count=((len(inspector_vm.related_validation_findings) + len(inspector_vm.related_execution_findings)) if inspector_vm is not None else 0),
        editability=inspector_vm.status_summary.editability if inspector_vm is not None else "unknown",
        has_execution_context=bool(inspector_vm is not None and inspector_vm.status_summary.execution_state not in {None, "idle", "unknown"}),
    )
    review_state = ConfigurationReviewStateView(
        validation_status=validation_vm.overall_status if validation_vm is not None else "unknown",
        blocking_count=validation_vm.summary.blocking_count if validation_vm is not None else 0,
        warning_count=validation_vm.summary.warning_count if validation_vm is not None else 0,
        confirmation_count=validation_vm.summary.confirmation_count if validation_vm is not None else 0,
        designer_session_mode=designer_vm.session_mode if designer_vm is not None else "idle",
        approval_stage=designer_vm.approval_state.current_stage if designer_vm is not None else None,
        commit_eligible=designer_vm.approval_state.commit_eligible if designer_vm is not None else False,
    )

    if inspector_vm is None or inspector_vm.object_type in {"none", "unknown"}:
        workspace_status = "awaiting_selection"
    elif storage_role != "working_save" and inspector_vm.status_summary.execution_state in {"running", "failed", "completed", "success", "partial"}:
        workspace_status = "run_review"
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        workspace_status = "blocked"
    elif designer_vm is not None and designer_vm.approval_state.current_stage not in {None, "idle", "none"}:
        workspace_status = "designer_review"
    else:
        workspace_status = "configuring"

    can_submit_designer_request = designer_vm.request_state.can_submit if designer_vm is not None else False
    can_commit_configuration = any(
        action.action_id == "commit_snapshot" and action.enabled
        for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    )
    local_actions = _workspace_local_actions(
        workspace_status=workspace_status,
        app_language=app_language,
        action_schema=action_schema,
        selection_summary=selection_summary,
        review_state=review_state,
    )
    readiness = _configuration_readiness(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        review_state=review_state,
        local_actions=local_actions,
        app_language=app_language,
    )
    focus_hint = _configuration_focus_hint(
        workspace_status=workspace_status,
        inspector_vm=inspector_vm,
        selection_summary=selection_summary,
        local_actions=local_actions,
        app_language=app_language,
    )
    workspace_handoff = _configuration_handoff(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        local_actions=local_actions,
        app_language=app_language,
    )
    action_shortcuts = _configuration_action_shortcuts(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        local_actions=local_actions,
        app_language=app_language,
    )
    attention_targets = _configuration_attention_targets(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        workspace_handoff=workspace_handoff,
        local_actions=local_actions,
        app_language=app_language,
    )
    progress_stages = _configuration_progress_stages(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        review_state=review_state,
        local_actions=local_actions,
        app_language=app_language,
    )
    closure_barriers = _configuration_closure_barriers(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        workspace_handoff=workspace_handoff,
        attention_targets=attention_targets,
        review_state=review_state,
        local_actions=local_actions,
        app_language=app_language,
    )
    closure_verdict = _configuration_closure_verdict(
        workspace_status=workspace_status,
        selection_summary=selection_summary,
        closure_barriers=closure_barriers,
        app_language=app_language,
    )
    workspace_explanation = explanation or _workspace_explanation(
        workspace_status=workspace_status,
        app_language=app_language,
        validation_vm=validation_vm,
        designer_vm=designer_vm,
    )
    suggested_actions = _workspace_suggested_actions(
        workspace_status=workspace_status,
        local_actions=local_actions,
    )

    return NodeConfigurationWorkspaceViewModel(
        workspace_status=workspace_status,
        workspace_status_label=ui_text(f"workspace.configuration.status.{workspace_status}", app_language=app_language, fallback_text=workspace_status.replace("_", " ")),
        storage_role=storage_role,
        inspector=inspector_vm,
        validation=validation_vm,
        designer=designer_vm,
        coordination=coordination_vm,
        action_schema=action_schema,
        selection_summary=selection_summary,
        review_state=review_state,
        readiness=readiness,
        focus_hint=focus_hint,
        workspace_handoff=workspace_handoff,
        can_edit_configuration=storage_role == "working_save" and selection_summary.object_type not in {"none", "unknown"},
        can_submit_designer_request=can_submit_designer_request,
        can_commit_configuration=can_commit_configuration,
        local_actions=local_actions,
        action_shortcuts=action_shortcuts,
        attention_targets=attention_targets,
        progress_stages=progress_stages,
        closure_barriers=closure_barriers,
        closure_verdict=closure_verdict,
        explanation=workspace_explanation,
        suggested_actions=suggested_actions,
    )


__all__ = [
    "ConfigurationActionShortcutView",
    "ConfigurationAttentionTargetView",
    "ConfigurationClosureBarrierView",
    "ConfigurationClosureVerdictView",
    "ConfigurationFocusHintView",
    "ConfigurationProgressStageView",
    "ConfigurationReadinessView",
    "ConfigurationReviewStateView",
    "ConfigurationSelectionSummaryView",
    "ConfigurationWorkspaceHandoffView",
    "NodeConfigurationWorkspaceViewModel",
    "read_node_configuration_workspace_view_model",
]
