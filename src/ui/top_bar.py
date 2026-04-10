from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.nex_contract import ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class WorkspaceBreadcrumbView:
    workspace_ref: str | None = None
    workspace_title: str | None = None
    role_hint: str = "none"


@dataclass(frozen=True)
class StorageRoleBadgeView:
    storage_role: str = "none"
    label: str | None = None
    severity: str = "neutral"


@dataclass(frozen=True)
class GlobalStatusSummaryView:
    overall_status: str = "ready"
    overall_status_label: str | None = None
    blocking_count: int = 0
    warning_count: int = 0
    pending_approval_count: int = 0
    execution_status: str = "idle"
    execution_status_label: str | None = None


@dataclass(frozen=True)
class PrimaryActionButtonView:
    action_id: str
    label: str
    emphasis: str = "secondary"
    enabled: bool = False
    reason_disabled: str | None = None
    requires_confirmation: bool = False
    destructive: bool = False


@dataclass(frozen=True)
class ModeOptionView:
    mode_id: str
    label: str
    active: bool = False
    available: bool = True


@dataclass(frozen=True)
class BuilderTopBarViewModel:
    topbar_status: str = "ready"
    source_role: str = "none"
    breadcrumb: WorkspaceBreadcrumbView = field(default_factory=WorkspaceBreadcrumbView)
    storage_badge: StorageRoleBadgeView = field(default_factory=StorageRoleBadgeView)
    global_status: GlobalStatusSummaryView = field(default_factory=GlobalStatusSummaryView)
    primary_actions: list[PrimaryActionButtonView] = field(default_factory=list)
    mode_options: list[ModeOptionView] = field(default_factory=list)
    quick_jump_placeholder: str | None = None
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


def _workspace_ref(source) -> str | None:
    if isinstance(source, WorkingSaveModel):
        return f"working_save:{source.meta.working_save_id}"
    if isinstance(source, CommitSnapshotModel):
        return f"commit_snapshot:{source.meta.commit_id}"
    if isinstance(source, ExecutionRecordModel):
        return f"execution_record:{source.meta.run_id}"
    return None


def _workspace_title(source) -> str | None:
    if isinstance(source, WorkingSaveModel):
        return source.meta.name or source.meta.working_save_id
    if isinstance(source, CommitSnapshotModel):
        return source.meta.name or source.meta.commit_id
    if isinstance(source, ExecutionRecordModel):
        return source.meta.run_id
    return None


def _role_severity(role: str) -> str:
    return {
        "working_save": "draft",
        "commit_snapshot": "approved",
        "execution_record": "runtime",
    }.get(role, "neutral")


def _role_label(role: str, *, app_language: str) -> str:
    return ui_text(f"storage.role.{role}", app_language=app_language, fallback_text=role.replace("_", " "))


def _execution_label(execution_status: str, *, app_language: str) -> str:
    if execution_status == "idle":
        return ui_text("execution.summary.idle", app_language=app_language, fallback_text="idle")
    return ui_text(f"execution.status.{execution_status}", app_language=app_language, fallback_text=execution_status.replace("_", " "))


def _overall_status(*, validation_view: ValidationPanelViewModel | None, execution_view: ExecutionPanelViewModel | None, approval_flow: DesignerApprovalFlowState | None) -> tuple[str, int, int, int]:
    blocking_count = validation_view.summary.blocking_count if validation_view is not None else 0
    warning_count = 0
    if validation_view is not None:
        warning_count += validation_view.summary.warning_count + validation_view.summary.confirmation_count
    pending_approval_count = 0
    if approval_flow is not None and approval_flow.current_stage not in {None, "idle", "none", "completed"}:
        pending_approval_count = 1

    if blocking_count:
        return "blocked", blocking_count, warning_count, pending_approval_count
    if execution_view is not None and execution_view.execution_status in {"running", "queued", "paused"}:
        return "active", blocking_count, warning_count, pending_approval_count
    if pending_approval_count:
        return "attention", blocking_count, warning_count, pending_approval_count
    if warning_count:
        return "warning", blocking_count, warning_count, pending_approval_count
    return "ready", blocking_count, warning_count, pending_approval_count


def _action_emphasis(action: BuilderActionView, *, is_primary_slot: bool) -> str:
    if action.destructive:
        return "destructive"
    if is_primary_slot:
        return "primary"
    return "secondary"


def _mode_options(*, role: str, execution_view: ExecutionPanelViewModel | None, approval_flow: DesignerApprovalFlowState | None, app_language: str) -> list[ModeOptionView]:
    review_active = approval_flow is not None and approval_flow.current_stage not in {None, "idle", "none", "completed"}
    run_active = execution_view is not None and execution_view.execution_status in {"running", "queued", "paused", "completed", "failed", "cancelled", "partial"}
    build_available = role in {"working_save", "commit_snapshot"}
    review_available = role in {"working_save", "commit_snapshot"}
    run_available = role in {"working_save", "commit_snapshot", "execution_record"}

    active_mode = "build"
    if run_active:
        active_mode = "run"
    elif review_active:
        active_mode = "review"

    return [
        ModeOptionView("build", ui_text("topbar.mode.build", app_language=app_language, fallback_text="Build"), active=active_mode == "build", available=build_available),
        ModeOptionView("review", ui_text("topbar.mode.review", app_language=app_language, fallback_text="Review"), active=active_mode == "review", available=review_available),
        ModeOptionView("run", ui_text("topbar.mode.run", app_language=app_language, fallback_text="Run"), active=active_mode == "run", available=run_available),
    ]


def read_builder_top_bar_view_model(
    source: SourceLike,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    storage_view: StoragePanelViewModel | None = None,
    validation_view: ValidationPanelViewModel | None = None,
    execution_view: ExecutionPanelViewModel | None = None,
    action_schema: BuilderActionSchemaView | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> BuilderTopBarViewModel:
    source_unwrapped = _unwrap(source)
    role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)
    storage_view = storage_view or (
        read_storage_view_model(
            source_unwrapped,
            latest_execution_record=(execution_record if execution_record is not None and not isinstance(source_unwrapped, ExecutionRecordModel) else None),
        ) if source_unwrapped is not None else None
    )
    validation_view = validation_view or (read_validation_panel_view_model(source_unwrapped, validation_report=validation_report, execution_record=execution_record) if source_unwrapped is not None else None)
    execution_view = execution_view or (read_execution_panel_view_model(source_unwrapped, execution_record=execution_record) if source_unwrapped is not None else None)
    action_schema = action_schema or read_builder_action_schema(source_unwrapped, storage_view=storage_view, validation_view=validation_view, execution_view=execution_view)

    overall_status, blocking_count, warning_count, pending_approval_count = _overall_status(
        validation_view=validation_view,
        execution_view=execution_view,
        approval_flow=approval_flow,
    )

    primary_actions = [
        PrimaryActionButtonView(
            action_id=action.action_id,
            label=action.label,
            emphasis=_action_emphasis(action, is_primary_slot=True),
            enabled=action.enabled,
            reason_disabled=action.reason_disabled,
            requires_confirmation=action.requires_confirmation,
            destructive=action.destructive,
        )
        for action in action_schema.primary_actions
    ]

    execution_status = execution_view.execution_status if execution_view is not None else "idle"
    topbar_status = "empty" if source_unwrapped is None else overall_status

    return BuilderTopBarViewModel(
        topbar_status=topbar_status,
        source_role=role,
        breadcrumb=WorkspaceBreadcrumbView(
            workspace_ref=_workspace_ref(source_unwrapped),
            workspace_title=_workspace_title(source_unwrapped),
            role_hint=role,
        ),
        storage_badge=StorageRoleBadgeView(
            storage_role=role,
            label=_role_label(role, app_language=app_language),
            severity=_role_severity(role),
        ),
        global_status=GlobalStatusSummaryView(
            overall_status=overall_status,
            overall_status_label=ui_text(f"topbar.status.{overall_status}", app_language=app_language, fallback_text=overall_status.replace("_", " ")),
            blocking_count=blocking_count,
            warning_count=warning_count,
            pending_approval_count=pending_approval_count,
            execution_status=execution_status,
            execution_status_label=_execution_label(execution_status, app_language=app_language),
        ),
        primary_actions=primary_actions,
        mode_options=_mode_options(role=role, execution_view=execution_view, approval_flow=approval_flow, app_language=app_language),
        quick_jump_placeholder=ui_text("palette.placeholder", app_language=app_language, fallback_text="Search nodes, findings, runs, actions"),
        explanation=explanation,
    )


__all__ = [
    "BuilderTopBarViewModel",
    "GlobalStatusSummaryView",
    "ModeOptionView",
    "PrimaryActionButtonView",
    "StorageRoleBadgeView",
    "WorkspaceBreadcrumbView",
    "read_builder_top_bar_view_model",
]
