from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.designer_panel import DesignerPanelViewModel
from src.ui.external_input_guidance import detect_external_input_kind
from src.ui.execution_panel import ExecutionPanelViewModel
from src.ui.i18n import ui_text
from src.ui.validation_panel import ValidationPanelViewModel


@dataclass(frozen=True)
class ContextualHelpActionView:
    action_id: str
    label: str
    target: str


@dataclass(frozen=True)
class ContextualHelpView:
    visible: bool = False
    stage: str = "hidden"
    title: str | None = None
    summary: str | None = None
    suggested_actions: tuple[ContextualHelpActionView, ...] = ()
    deep_help_enabled: bool = False


@dataclass(frozen=True)
class PrivacyTransparencyFactView:
    fact_id: str
    label: str
    value: str
    severity: str = "info"


@dataclass(frozen=True)
class PrivacyTransparencyView:
    visible: bool = False
    title: str | None = None
    summary: str | None = None
    facts: tuple[PrivacyTransparencyFactView, ...] = ()
    requires_acknowledgement: bool = False
    acknowledgement_action_label: str | None = None


@dataclass(frozen=True)
class MobileFirstRunStepView:
    step_id: str
    label: str
    status: str


@dataclass(frozen=True)
class MobileFirstRunView:
    visible: bool = False
    viewport_tier: str = "standard_desktop"
    compact_mode: bool = False
    steps: tuple[MobileFirstRunStepView, ...] = ()
    progress_label: str | None = None
    primary_action_label: str | None = None
    primary_action_target: str | None = None
    summary: str | None = None


def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source: Any) -> str:
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _ui_metadata(source: Any) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}


def _viewport_tier(metadata: Mapping[str, Any]) -> str:
    explicit = metadata.get("viewport_tier")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    if bool(metadata.get("mobile_first_run")):
        return "mobile"
    form_factor = str(metadata.get("device_form_factor") or "").lower().strip()
    if form_factor in {"mobile", "phone", "tablet", "touch"}:
        return "mobile" if form_factor in {"mobile", "phone", "touch"} else "tablet"
    return "standard_desktop"


def _is_mobile_tier(viewport_tier: str) -> bool:
    return viewport_tier in {"mobile", "tablet", "small_touch", "narrow_workspace", "split_view"}

    nodes = list(source.circuit.nodes or [])
    plugins = source.resources.plugins if isinstance(source.resources.plugins, Mapping) else {}
    for node in nodes:
        execution = node.get("execution") if isinstance(node, Mapping) else None
        plugin = execution.get("plugin") if isinstance(execution, Mapping) else None
        plugin_id = None
        if isinstance(plugin, Mapping):
            plugin_id = str(plugin.get("plugin_id") or plugin.get("id") or "")
        if isinstance(plugin_id, str) and plugin_id.endswith("file_reader"):
            return True, "file"
        if isinstance(plugin_id, str) and plugin_id.endswith("url_reader"):
            return True, "url"
    for plugin_id in plugins:
        if str(plugin_id).endswith("file_reader"):
            return True, "file"
        if str(plugin_id).endswith("url_reader"):
            return True, "url"
    return False, None


def _provider_access_summary(designer_vm: DesignerPanelViewModel | None, *, app_language: str) -> tuple[str, str, str]:
    if designer_vm is not None:
        if designer_vm.provider_inline_key_entry.has_connected_provider:
            session_connected = any(option.status == "session_connected" for option in designer_vm.provider_inline_key_entry.preset_options)
            if session_connected:
                return (
                    ui_text("phase6.privacy.fact.provider_access", app_language=app_language, fallback_text="Provider access"),
                    ui_text("phase6.privacy.provider.session_only", app_language=app_language, fallback_text="Session-only key"),
                    "warning",
                )
            return (
                ui_text("phase6.privacy.fact.provider_access", app_language=app_language, fallback_text="Provider access"),
                ui_text("phase6.privacy.provider.configured", app_language=app_language, fallback_text="Configured provider"),
                "info",
            )
    return (
        ui_text("phase6.privacy.fact.provider_access", app_language=app_language, fallback_text="Provider access"),
        ui_text("phase6.privacy.provider.none", app_language=app_language, fallback_text="No provider connected"),
        "warning",
    )


def read_privacy_transparency_view(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    designer_view: DesignerPanelViewModel | None,
    app_language: str,
) -> PrivacyTransparencyView:
    source_unwrapped = _unwrap(source)
    role = _storage_role(source_unwrapped)
    metadata = _ui_metadata(source_unwrapped)
    if role not in {"working_save", "commit_snapshot"}:
        return PrivacyTransparencyView()

    facts: list[PrivacyTransparencyFactView] = []
    provider_label, provider_value, provider_severity = _provider_access_summary(designer_view, app_language=app_language)
    facts.append(PrivacyTransparencyFactView("provider_access", provider_label, provider_value, provider_severity))

    external_input, external_input_kind = detect_external_input_kind(source_unwrapped)
    if external_input:
        external_value = ui_text(
            f"phase6.privacy.external_input.{external_input_kind}",
            app_language=app_language,
            fallback_text=("Reads from a file" if external_input_kind == "file" else "Reads from a URL"),
        )
    else:
        external_value = ui_text("phase6.privacy.external_input.none", app_language=app_language, fallback_text="No external file or URL input")
    facts.append(
        PrivacyTransparencyFactView(
            "external_input",
            ui_text("phase6.privacy.fact.external_input", app_language=app_language, fallback_text="External input"),
            external_value,
            "info" if external_input else "neutral",
        )
    )

    storage_value = ui_text(
        f"phase6.privacy.storage_boundary.{role}",
        app_language=app_language,
        fallback_text=(
            "Local working-save continuity only" if role == "working_save" else "Approved snapshot / review state"
        ),
    )
    facts.append(
        PrivacyTransparencyFactView(
            "storage_boundary",
            ui_text("phase6.privacy.fact.storage_boundary", app_language=app_language, fallback_text="Storage boundary"),
            storage_value,
            "info",
        )
    )

    if isinstance(source_unwrapped, WorkingSaveModel) and isinstance(metadata.get("provider_session_keys"), Mapping) and metadata.get("provider_session_keys"):
        facts.append(
            PrivacyTransparencyFactView(
                "session_key_persistence",
                ui_text("phase6.privacy.fact.session_key_persistence", app_language=app_language, fallback_text="Session keys"),
                ui_text("phase6.privacy.session_key.not_written", app_language=app_language, fallback_text="Session keys stay in working-save UI state and are not written to commit snapshots."),
                "warning",
            )
        )

    requires_ack = bool(external_input or provider_severity == "warning") and not bool(metadata.get("privacy_notice_acknowledged"))
    summary = ui_text(
        "phase6.privacy.summary",
        app_language=app_language,
        fallback_text="Review how your data is routed before the first run.",
    )
    return PrivacyTransparencyView(
        visible=True,
        title=ui_text("phase6.privacy.title", app_language=app_language, fallback_text="Privacy and data handling"),
        summary=summary,
        facts=tuple(facts),
        requires_acknowledgement=requires_ack,
        acknowledgement_action_label=(ui_text("phase6.privacy.acknowledge", app_language=app_language, fallback_text="I understand") if requires_ack else None),
    )


def read_contextual_help_view(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    beginner_mode: bool,
    empty_workspace_mode: bool,
    validation_view: ValidationPanelViewModel | None,
    designer_view: DesignerPanelViewModel | None,
    execution_view: ExecutionPanelViewModel | None,
    app_language: str,
) -> ContextualHelpView:
    source_unwrapped = _unwrap(source)
    if _storage_role(source_unwrapped) not in {"working_save", "commit_snapshot", "execution_record"}:
        return ContextualHelpView()

    if empty_workspace_mode:
        return ContextualHelpView(
            visible=True,
            stage="start",
            title=ui_text("phase6.help.start.title", app_language=app_language, fallback_text="Start with a goal"),
            summary=ui_text("phase6.help.start.summary", app_language=app_language, fallback_text="Describe your goal and Nexa will prepare a workflow draft you can review before running."),
            suggested_actions=(
                ContextualHelpActionView("open_designer", ui_text("beginner.onboarding.start.action", app_language=app_language, fallback_text="Open Designer"), "designer"),
                ContextualHelpActionView("browse_templates", ui_text("phase6.help.start.templates", app_language=app_language, fallback_text="Browse templates"), "designer.templates"),
                ContextualHelpActionView("open_file_input", ui_text("phase6.help.start.file", app_language=app_language, fallback_text="Start from a file"), "designer.external_input.file"),
                ContextualHelpActionView("enter_url_input", ui_text("phase6.help.start.url", app_language=app_language, fallback_text="Start from a web address"), "designer.external_input.url"),
            ),
            deep_help_enabled=not beginner_mode,
        )

    if validation_view is not None and validation_view.overall_status == "blocked":
        summary = validation_view.beginner_summary.cause or (validation_view.blocking_findings[0].message if validation_view.blocking_findings else None)
        return ContextualHelpView(
            visible=True,
            stage="fix",
            title=ui_text("phase6.help.fix.title", app_language=app_language, fallback_text="Fix the top issue first"),
            summary=summary,
            suggested_actions=(
                ContextualHelpActionView(
                    "focus_top_issue",
                    validation_view.beginner_summary.next_action_label or ui_text("phase6.help.fix.action", app_language=app_language, fallback_text="Fix this step"),
                    "validation",
                ),
            ),
            deep_help_enabled=True,
        )

    if designer_view is not None and designer_view.preview_state.preview_status == "ready" and designer_view.approval_state.final_outcome not in {"approved_for_commit", "committed"}:
        return ContextualHelpView(
            visible=True,
            stage="review",
            title=ui_text("phase6.help.review.title", app_language=app_language, fallback_text="Review before running"),
            summary=designer_view.preview_state.one_sentence_summary or ui_text("phase6.help.review.summary", app_language=app_language, fallback_text="Confirm the proposed workflow before you run it."),
            suggested_actions=(
                ContextualHelpActionView("review_workflow", ui_text("beginner.onboarding.review.action", app_language=app_language, fallback_text="Review workflow"), "designer"),
            ),
            deep_help_enabled=not beginner_mode,
        )

    if execution_view is not None and execution_view.waiting_feedback.visible:
        return ContextualHelpView(
            visible=True,
            stage="wait",
            title=execution_view.waiting_feedback.title,
            summary=execution_view.waiting_feedback.summary,
            suggested_actions=(
                ContextualHelpActionView(
                    "watch_progress",
                    execution_view.waiting_feedback.next_action_label or ui_text("phase6.help.wait.action", app_language=app_language, fallback_text="Watch progress"),
                    execution_view.waiting_feedback.next_action_target or "execution",
                ),
            ),
            deep_help_enabled=True,
        )

    if execution_view is not None and execution_view.result_reading.visible:
        return ContextualHelpView(
            visible=True,
            stage="result",
            title=execution_view.result_reading.title or ui_text("phase6.help.result.title", app_language=app_language, fallback_text="Read the result"),
            summary=execution_view.result_reading.summary,
            suggested_actions=(
                ContextualHelpActionView("open_output", ui_text("phase6.help.result.action", app_language=app_language, fallback_text="Open result"), "execution.output"),
            ),
            deep_help_enabled=True,
        )

    return ContextualHelpView(
        visible=beginner_mode,
        stage="general",
        title=(ui_text("phase6.help.general.title", app_language=app_language, fallback_text="Need help?")) if beginner_mode else None,
        summary=(ui_text("phase6.help.general.summary", app_language=app_language, fallback_text="Nexa will guide you through review, run, and result reading one step at a time.")) if beginner_mode else None,
        suggested_actions=((ContextualHelpActionView("open_help", ui_text("phase6.help.general.action", app_language=app_language, fallback_text="Open help"), "help"),) if beginner_mode else ()),
        deep_help_enabled=not beginner_mode,
    )


def _mobile_step_statuses(
    *,
    empty_workspace_mode: bool,
    designer_view: DesignerPanelViewModel | None,
    execution_view: ExecutionPanelViewModel | None,
) -> dict[str, str]:
    enter_goal = "complete" if not empty_workspace_mode and designer_view is not None and bool(designer_view.request_state.current_request_text) else "active"
    review = "pending"
    approve = "pending"
    run = "pending"
    read = "pending"

    if designer_view is not None and designer_view.preview_state.preview_status == "ready":
        review = "active"
    if designer_view is not None and designer_view.approval_state.commit_eligible:
        review = "complete"
        approve = "active"
    if designer_view is not None and designer_view.approval_state.final_outcome in {"approved_for_commit", "committed"}:
        approve = "complete"
        run = "active"
    if execution_view is not None and execution_view.execution_status in {"running", "queued", "completed", "failed", "partial", "cancelled"}:
        run = "active" if execution_view.execution_status in {"running", "queued"} else "complete"
    if execution_view is not None and execution_view.execution_status == "completed" and execution_view.latest_outputs:
        read = "active"
    return {
        "enter_goal": enter_goal,
        "review_preview": review,
        "approve": approve,
        "run": run,
        "read_result": read,
    }


def read_mobile_first_run_view(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    beginner_mode: bool,
    empty_workspace_mode: bool,
    designer_view: DesignerPanelViewModel | None,
    execution_view: ExecutionPanelViewModel | None,
    app_language: str,
) -> MobileFirstRunView:
    source_unwrapped = _unwrap(source)
    metadata = _ui_metadata(source_unwrapped)
    viewport_tier = _viewport_tier(metadata)
    if not beginner_mode or not _is_mobile_tier(viewport_tier):
        return MobileFirstRunView(viewport_tier=viewport_tier)

    statuses = _mobile_step_statuses(
        empty_workspace_mode=empty_workspace_mode,
        designer_view=designer_view,
        execution_view=execution_view,
    )
    ordered_steps = (
        ("enter_goal", ui_text("phase6.mobile.step.enter_goal", app_language=app_language, fallback_text="Enter goal")),
        ("review_preview", ui_text("phase6.mobile.step.review_preview", app_language=app_language, fallback_text="Review preview")),
        ("approve", ui_text("phase6.mobile.step.approve", app_language=app_language, fallback_text="Approve")),
        ("run", ui_text("phase6.mobile.step.run", app_language=app_language, fallback_text="Run")),
        ("read_result", ui_text("phase6.mobile.step.read_result", app_language=app_language, fallback_text="Read result")),
    )
    steps = tuple(MobileFirstRunStepView(step_id=step_id, label=label, status=statuses.get(step_id, "pending")) for step_id, label in ordered_steps)
    complete_count = sum(1 for step in steps if step.status == "complete")
    active_step = next((step for step in steps if step.status == "active"), steps[-1])
    primary_target = {
        "enter_goal": "designer",
        "review_preview": "designer",
        "approve": "designer",
        "run": "execution",
        "read_result": "execution.output",
    }.get(active_step.step_id, "designer")
    return MobileFirstRunView(
        visible=True,
        viewport_tier=viewport_tier,
        compact_mode=True,
        steps=steps,
        progress_label=ui_text(
            "phase6.mobile.progress",
            app_language=app_language,
            fallback_text="{complete_count}/5 steps complete",
            complete_count=complete_count,
        ),
        primary_action_label=active_step.label,
        primary_action_target=primary_target,
        summary=ui_text(
            "phase6.mobile.summary",
            app_language=app_language,
            fallback_text="Mobile first-run keeps only the core path: goal → preview → approve → run → result.",
        ),
    )


__all__ = [
    "ContextualHelpActionView",
    "ContextualHelpView",
    "PrivacyTransparencyFactView",
    "PrivacyTransparencyView",
    "MobileFirstRunStepView",
    "MobileFirstRunView",
    "read_contextual_help_view",
    "read_mobile_first_run_view",
    "read_privacy_transparency_view",
]
