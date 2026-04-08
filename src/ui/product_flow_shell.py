from __future__ import annotations

from dataclasses import dataclass, field

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
from src.ui.builder_dispatch_hub import BuilderDispatchHubViewModel, read_builder_dispatch_hub_view_model
from src.ui.builder_end_user_flow_hub import BuilderEndUserFlowHubViewModel, read_builder_end_user_flow_hub_view_model
from src.ui.builder_execution_adapter_hub import BuilderExecutionAdapterHubViewModel, read_builder_execution_adapter_hub_view_model
from src.ui.builder_shell import BuilderShellViewModel, read_builder_shell_view_model
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.product_flow_journey import ProductFlowJourneyViewModel, read_product_flow_journey_view_model
from src.ui.product_flow_runbook import ProductFlowRunbookViewModel, read_product_flow_runbook_view_model
from src.ui.product_flow_handoff import ProductFlowHandoffViewModel, read_product_flow_handoff_view_model
from src.ui.product_flow_readiness import ProductFlowReadinessViewModel, read_product_flow_readiness_view_model
from src.ui.product_flow_e2e_path import ProductFlowE2EPathViewModel, read_product_flow_e2e_path_view_model


@dataclass(frozen=True)
class ProductFlowStageView:
    stage_id: str = "build"
    stage_label: str | None = None
    blocking_count: int = 0
    warning_count: int = 0
    pending_approval_count: int = 0
    live_execution: bool = False
    visible_event_count: int = 0
    visible_artifact_count: int = 0
    visible_change_count: int = 0


@dataclass(frozen=True)
class ProductFlowFocusView:
    active_workspace_id: str = "visual_editor"
    active_workspace_label: str | None = None
    active_right_panel_id: str = "inspector"
    active_right_panel_label: str | None = None
    active_bottom_panel_id: str = "storage"
    active_bottom_panel_label: str | None = None
    recommended_action_id: str | None = None
    recommended_flow_id: str | None = None
    focus_reason: str | None = None


@dataclass(frozen=True)
class ProductFlowSurfaceTargetView:
    target_id: str
    label: str
    location: str
    workspace_id: str
    active: bool = False
    badge_count: int = 0
    status: str = "ready"


@dataclass(frozen=True)
class ProductFlowShellViewModel:
    shell_status: str = "ready"
    shell_status_label: str | None = None
    storage_role: str = "none"
    stage: ProductFlowStageView = field(default_factory=ProductFlowStageView)
    focus: ProductFlowFocusView = field(default_factory=ProductFlowFocusView)
    shell: BuilderShellViewModel | None = None
    workflow_hub: BuilderWorkflowHubViewModel | None = None
    dispatch_hub: BuilderDispatchHubViewModel | None = None
    execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None
    end_user_flow_hub: BuilderEndUserFlowHubViewModel | None = None
    journey: ProductFlowJourneyViewModel | None = None
    runbook: ProductFlowRunbookViewModel | None = None
    handoff: ProductFlowHandoffViewModel | None = None
    readiness: ProductFlowReadinessViewModel | None = None
    e2e_path: ProductFlowE2EPathViewModel | None = None
    right_stack_targets: list[ProductFlowSurfaceTargetView] = field(default_factory=list)
    bottom_dock_targets: list[ProductFlowSurfaceTargetView] = field(default_factory=list)
    command_entry_count: int = 0
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


def _panel_label(panel_id: str, *, app_language: str) -> str:
    return ui_text(f"panel.{panel_id}", app_language=app_language, fallback_text=panel_id.replace("_", " ").title())


def _workspace_label(workspace_id: str, *, app_language: str) -> str:
    return ui_text(f"workspace.{workspace_id}.name", app_language=app_language, fallback_text=workspace_id.replace("_", " ").title())


def _badge_count(shell_vm: BuilderShellViewModel, panel_id: str) -> int:
    if shell_vm is None:
        return 0
    for badge in shell_vm.coordination.panel_badges:
        if badge.panel_id == panel_id:
            return badge.count
    return 0


def _stage_id(shell_vm: BuilderShellViewModel | None, workflow_hub: BuilderWorkflowHubViewModel | None) -> str:
    if shell_vm is not None and shell_vm.shell_mode == "runtime_monitoring":
        return "run"
    if shell_vm is not None and shell_vm.shell_mode == "designer_review":
        return "review"
    if workflow_hub is not None and workflow_hub.active_workflow_id == "execution_launch":
        return "run"
    if workflow_hub is not None and workflow_hub.active_workflow_id == "proposal_commit":
        return "review"
    return "build"


def _pending_approval_count(shell_vm: BuilderShellViewModel | None) -> int:
    if shell_vm is None or shell_vm.designer is None:
        return 0
    unanswered = shell_vm.designer.approval_state.unanswered_decision_count
    if unanswered:
        return unanswered
    if shell_vm.designer.approval_state.current_stage not in {None, "idle", "none", "completed"}:
        return 1
    return 0


def _warning_count(shell_vm: BuilderShellViewModel | None) -> int:
    if shell_vm is None or shell_vm.validation is None:
        return 0
    return shell_vm.validation.summary.warning_count + shell_vm.validation.summary.confirmation_count


def _blocking_count(shell_vm: BuilderShellViewModel | None) -> int:
    if shell_vm is None or shell_vm.validation is None:
        return 0
    return shell_vm.validation.summary.blocking_count


def _change_count(shell_vm: BuilderShellViewModel | None) -> int:
    if shell_vm is None or shell_vm.diff is None:
        return 0
    return shell_vm.diff.summary.total_change_count


def _focus(shell_vm: BuilderShellViewModel | None, stage_id: str, recommended_action_id: str | None, recommended_flow_id: str | None, *, app_language: str, handoff: ProductFlowHandoffViewModel | None = None) -> ProductFlowFocusView:
    if shell_vm is None:
        return ProductFlowFocusView()

    active_workspace_id = shell_vm.active_workspace_id
    focus_reason = "steady_state"

    if stage_id == "run":
        active_workspace_id = "runtime_monitoring"
        if shell_vm.execution is not None and shell_vm.execution.execution_status in {"running", "queued"}:
            active_right_panel_id = "execution"
            active_bottom_panel_id = "trace_timeline" if shell_vm.trace_timeline is not None and shell_vm.trace_timeline.events else "artifact"
            focus_reason = "live_execution"
        elif shell_vm.trace_timeline is not None and shell_vm.trace_timeline.events:
            active_right_panel_id = "trace_timeline"
            active_bottom_panel_id = "artifact" if shell_vm.artifact is not None and shell_vm.artifact.artifact_list else "execution"
            focus_reason = "trace_review"
        else:
            active_right_panel_id = "artifact" if shell_vm.artifact is not None and shell_vm.artifact.artifact_list else "execution"
            active_bottom_panel_id = "diff" if shell_vm.diff is not None else "storage"
            focus_reason = "historical_run_review"
    elif stage_id == "review":
        active_workspace_id = "node_configuration"
        if shell_vm.designer is not None and shell_vm.designer.approval_state.current_stage not in {None, "idle", "none", "completed"}:
            active_right_panel_id = "designer"
            active_bottom_panel_id = "diff" if shell_vm.diff is not None else "validation"
            focus_reason = "proposal_approval"
        elif shell_vm.validation is not None and shell_vm.validation.overall_status == "blocked":
            active_right_panel_id = "validation"
            active_bottom_panel_id = "diff" if shell_vm.diff is not None else "storage"
            focus_reason = "blocked_review"
        else:
            active_right_panel_id = "inspector"
            active_bottom_panel_id = "diff" if shell_vm.diff is not None else "storage"
            focus_reason = "configuration_review"
    else:
        active_workspace_id = "visual_editor"
        if shell_vm.coordination.active_panel in {"designer", "validation", "inspector"}:
            active_right_panel_id = shell_vm.coordination.active_panel
        elif shell_vm.inspector is not None and shell_vm.inspector.object_type not in {"none", "unknown"}:
            active_right_panel_id = "inspector"
        else:
            active_right_panel_id = "designer"
        if shell_vm.diff is not None:
            active_bottom_panel_id = "diff"
            focus_reason = "preview_compare"
        elif shell_vm.validation is not None and (
            shell_vm.validation.summary.blocking_count
            or shell_vm.validation.summary.warning_count
            or shell_vm.validation.summary.confirmation_count
        ):
            active_bottom_panel_id = "validation"
            focus_reason = "validation_followup"
        else:
            active_bottom_panel_id = "storage"
            focus_reason = "draft_edit"

    if handoff is not None and handoff.primary_workspace_id is not None and handoff.primary_panel_id is not None:
        if stage_id != "run" and handoff.primary_action_id is not None and handoff.primary_enabled:
            active_workspace_id = handoff.primary_workspace_id
            active_right_panel_id = handoff.primary_panel_id
            focus_reason = "handoff_primary"
        elif handoff.primary_enabled and not handoff.primary_complete:
            active_workspace_id = handoff.primary_workspace_id
            active_right_panel_id = handoff.primary_panel_id
            focus_reason = "handoff_primary"
        elif handoff.followthrough_available and handoff.followthrough_workspace_id is not None and handoff.followthrough_panel_id is not None:
            active_workspace_id = handoff.followthrough_workspace_id
            active_right_panel_id = handoff.followthrough_panel_id
            focus_reason = "handoff_followthrough"

    return ProductFlowFocusView(
        active_workspace_id=active_workspace_id,
        active_workspace_label=_workspace_label(active_workspace_id, app_language=app_language),
        active_right_panel_id=active_right_panel_id,
        active_right_panel_label=_panel_label(active_right_panel_id, app_language=app_language),
        active_bottom_panel_id=active_bottom_panel_id,
        active_bottom_panel_label=_panel_label(active_bottom_panel_id, app_language=app_language),
        recommended_action_id=recommended_action_id,
        recommended_flow_id=recommended_flow_id,
        focus_reason=focus_reason,
    )


def _surface_targets(shell_vm: BuilderShellViewModel | None, *, app_language: str, focus: ProductFlowFocusView) -> tuple[list[ProductFlowSurfaceTargetView], list[ProductFlowSurfaceTargetView]]:
    if shell_vm is None:
        return [], []

    right_stack_ids = ["inspector", "designer", "validation", "execution", "trace_timeline", "artifact"]
    bottom_dock_ids = ["validation", "storage", "execution", "trace_timeline", "artifact", "diff"]

    status_by_panel = {
        "inspector": "ready" if shell_vm.inspector is not None else "empty",
        "designer": shell_vm.designer.request_state.request_status if shell_vm.designer is not None else "empty",
        "validation": shell_vm.validation.overall_status if shell_vm.validation is not None else "empty",
        "storage": shell_vm.storage.lifecycle_summary.current_stage if shell_vm.storage is not None else "empty",
        "execution": shell_vm.execution.execution_status if shell_vm.execution is not None else "empty",
        "trace_timeline": shell_vm.trace_timeline.timeline_status if shell_vm.trace_timeline is not None else "empty",
        "artifact": shell_vm.artifact.viewer_status if shell_vm.artifact is not None else "empty",
        "diff": shell_vm.diff.viewer_status if shell_vm.diff is not None else "hidden",
    }
    workspace_by_panel = {
        "inspector": "node_configuration",
        "designer": "node_configuration",
        "validation": "node_configuration",
        "storage": "visual_editor",
        "execution": "runtime_monitoring",
        "trace_timeline": "runtime_monitoring",
        "artifact": "runtime_monitoring",
        "diff": "visual_editor",
    }

    right_stack = [
        ProductFlowSurfaceTargetView(
            target_id=panel_id,
            label=_panel_label(panel_id, app_language=app_language),
            location="right_stack",
            workspace_id=workspace_by_panel[panel_id],
            active=focus.active_right_panel_id == panel_id,
            badge_count=_badge_count(shell_vm, panel_id),
            status=status_by_panel[panel_id],
        )
        for panel_id in right_stack_ids
        if status_by_panel[panel_id] != "empty" or panel_id in {"inspector", "designer", "validation"}
    ]
    bottom_dock = [
        ProductFlowSurfaceTargetView(
            target_id=panel_id,
            label=_panel_label(panel_id, app_language=app_language),
            location="bottom_dock",
            workspace_id=workspace_by_panel[panel_id],
            active=focus.active_bottom_panel_id == panel_id,
            badge_count=_badge_count(shell_vm, panel_id),
            status=status_by_panel[panel_id],
        )
        for panel_id in bottom_dock_ids
        if status_by_panel[panel_id] not in {"empty", "hidden"} or panel_id in {"validation", "storage"}
    ]
    return right_stack, bottom_dock


def read_product_flow_shell_view_model(
    source: SourceLike,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    selected_ref: str | None = None,
    live_events=None,
    diff_mode: str | None = None,
    diff_source=None,
    diff_target=None,
    selected_artifact_id: str | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> ProductFlowShellViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    shell_vm = read_builder_shell_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        selected_ref=selected_ref,
        live_events=live_events,
        diff_mode=diff_mode,
        diff_source=diff_source,
        diff_target=diff_target,
        selected_artifact_id=selected_artifact_id,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    workflow_hub = read_builder_workflow_hub_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        selected_ref=selected_ref,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        live_events=live_events,
        selected_artifact_id=selected_artifact_id,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    dispatch_hub = read_builder_dispatch_hub_view_model(source_unwrapped if source_unwrapped is not None else execution_record) if (source_unwrapped is not None or execution_record is not None) else None
    execution_adapter_hub = read_builder_execution_adapter_hub_view_model(source_unwrapped if source_unwrapped is not None else execution_record, dispatch_hub=dispatch_hub) if (source_unwrapped is not None or execution_record is not None) else None
    end_user_flow_hub = read_builder_end_user_flow_hub_view_model(source_unwrapped if source_unwrapped is not None else execution_record, execution_adapter_hub=execution_adapter_hub) if (source_unwrapped is not None or execution_record is not None) else None
    journey_vm = read_product_flow_journey_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        prefer_active_workflow_focus=True,
    ) if (source_unwrapped is not None or execution_record is not None) else None
    runbook_vm = read_product_flow_runbook_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey_vm,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    handoff_vm = read_product_flow_handoff_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey_vm,
        runbook=runbook_vm,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    readiness_vm = read_product_flow_readiness_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey_vm,
        runbook=runbook_vm,
        handoff=handoff_vm,
        end_user_flow_hub=end_user_flow_hub,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    e2e_path_vm = read_product_flow_e2e_path_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        workflow_hub=workflow_hub,
        journey=journey_vm,
        runbook=runbook_vm,
        handoff=handoff_vm,
        readiness=readiness_vm,
        end_user_flow_hub=end_user_flow_hub,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    stage_id = _stage_id(shell_vm, workflow_hub)
    recommended_flow_id = end_user_flow_hub.recommended_flow_id if end_user_flow_hub is not None else None
    recommended_action_id = (next((entry.action_id for entry in (runbook_vm.entries if runbook_vm is not None else []) if entry.entry_id == runbook_vm.recommended_entry_id and entry.action_id is not None), None) if runbook_vm is not None else None) or (execution_adapter_hub.recommended_action_id if execution_adapter_hub is not None else None)
    focus = _focus(shell_vm, stage_id, recommended_action_id, recommended_flow_id, app_language=app_language, handoff=handoff_vm)
    right_stack_targets, bottom_dock_targets = _surface_targets(shell_vm, app_language=app_language, focus=focus)

    stage = ProductFlowStageView(
        stage_id=stage_id,
        stage_label=ui_text(f"product.stage.{stage_id}", app_language=app_language, fallback_text=stage_id.title()),
        blocking_count=_blocking_count(shell_vm),
        warning_count=_warning_count(shell_vm),
        pending_approval_count=_pending_approval_count(shell_vm),
        live_execution=bool(shell_vm is not None and shell_vm.execution is not None and shell_vm.execution.execution_status in {"running", "queued"}),
        visible_event_count=len(shell_vm.trace_timeline.events) if shell_vm is not None and shell_vm.trace_timeline is not None else 0,
        visible_artifact_count=len(shell_vm.artifact.artifact_list) if shell_vm is not None and shell_vm.artifact is not None else 0,
        visible_change_count=_change_count(shell_vm),
    )

    if shell_vm is None:
        shell_status = "empty"
    elif stage.blocking_count:
        shell_status = "blocked"
    elif stage.stage_id == "run" and stage.live_execution:
        shell_status = "live_run"
    elif stage.stage_id == "review":
        shell_status = "review_focus"
    elif stage.stage_id == "build":
        shell_status = "build_focus"
    else:
        shell_status = "ready"

    return ProductFlowShellViewModel(
        shell_status=shell_status,
        shell_status_label=ui_text(f"product.status.{shell_status}", app_language=app_language, fallback_text=shell_status.replace("_", " ")),
        storage_role=storage_role,
        stage=stage,
        focus=focus,
        shell=shell_vm,
        workflow_hub=workflow_hub,
        dispatch_hub=dispatch_hub,
        execution_adapter_hub=execution_adapter_hub,
        end_user_flow_hub=end_user_flow_hub,
        journey=journey_vm,
        runbook=runbook_vm,
        handoff=handoff_vm,
        readiness=readiness_vm,
        e2e_path=e2e_path_vm,
        right_stack_targets=right_stack_targets,
        bottom_dock_targets=bottom_dock_targets,
        command_entry_count=(shell_vm.command_palette.enabled_entry_count if shell_vm is not None and shell_vm.command_palette is not None else 0),
        explanation=explanation,
    )


__all__ = [
    "ProductFlowStageView",
    "ProductFlowFocusView",
    "ProductFlowSurfaceTargetView",
    "ProductFlowShellViewModel",
    "read_product_flow_shell_view_model",
]
