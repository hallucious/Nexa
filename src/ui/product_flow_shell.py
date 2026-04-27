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
from src.ui.i18n import beginner_surface_active, ui_language_from_sources, ui_text
from src.ui.beginner_surface_gate import BEGINNER_ALLOWED_FALLBACK_PANEL_IDS, panel_ids_from_policy_surface_ids
from src.ui.product_flow_journey import ProductFlowJourneyViewModel, read_product_flow_journey_view_model
from src.ui.product_flow_runbook import ProductFlowRunbookViewModel, read_product_flow_runbook_view_model
from src.ui.product_flow_handoff import ProductFlowHandoffViewModel, read_product_flow_handoff_view_model
from src.ui.product_flow_readiness import ProductFlowReadinessViewModel, read_product_flow_readiness_view_model
from src.ui.product_flow_e2e_path import ProductFlowE2EPathViewModel, read_product_flow_e2e_path_view_model
from src.ui.product_flow_closure import ProductFlowClosureViewModel, read_product_flow_closure_view_model
from src.ui.product_flow_transition import ProductFlowTransitionViewModel, read_product_flow_transition_view_model
from src.ui.product_flow_gateway import ProductFlowGatewayViewModel, read_product_flow_gateway_view_model
from src.ui.product_flow_e2e_proof import ProductFlowE2EProofViewModel, read_product_flow_e2e_proof_view_model


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
    closure: ProductFlowClosureViewModel | None = None
    transition: ProductFlowTransitionViewModel | None = None
    gateway: ProductFlowGatewayViewModel | None = None
    e2e_proof: ProductFlowE2EProofViewModel | None = None
    right_stack_targets: list[ProductFlowSurfaceTargetView] = field(default_factory=list)
    bottom_dock_targets: list[ProductFlowSurfaceTargetView] = field(default_factory=list)
    command_entry_count: int = 0
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None

_ALLOWED_BEGINNER_FALLBACK_PANELS = BEGINNER_ALLOWED_FALLBACK_PANEL_IDS


def _suppressed_panel_ids(shell_vm: BuilderShellViewModel | None) -> set[str]:
    if shell_vm is None:
        return set()
    policy = shell_vm.beginner_surface_policy
    if not policy.visible or policy.can_open_advanced_surfaces:
        return set()
    return panel_ids_from_policy_surface_ids(policy.suppressed_surface_ids)


def _fallback_panel_id(shell_vm: BuilderShellViewModel, *, preferred: tuple[str, ...] = _ALLOWED_BEGINNER_FALLBACK_PANELS) -> str:
    available = {panel_id for panel_id in shell_vm.coordination.visible_panels}
    for panel_id in preferred:
        if panel_id in available:
            return panel_id
    if shell_vm.coordination.active_panel in available:
        return shell_vm.coordination.active_panel
    if available:
        return sorted(available)[0]
    return "designer" if shell_vm.designer is not None else "validation"


def _sanitize_focus_for_beginner_policy(shell_vm: BuilderShellViewModel, focus: ProductFlowFocusView, *, app_language: str) -> ProductFlowFocusView:
    suppressed = _suppressed_panel_ids(shell_vm)
    if not suppressed:
        return focus
    right_panel_id = focus.active_right_panel_id
    bottom_panel_id = focus.active_bottom_panel_id
    changed = False
    if right_panel_id in suppressed:
        right_panel_id = _fallback_panel_id(shell_vm, preferred=("execution", "validation", "designer", "inspector"))
        changed = True
    if bottom_panel_id in suppressed:
        bottom_panel_id = _fallback_panel_id(shell_vm, preferred=("validation", "execution", "designer", "inspector"))
        changed = True
    if not changed:
        return focus
    reason = focus.focus_reason or "steady_state"
    if not reason.endswith("_beginner_gated"):
        reason = f"{reason}_beginner_gated"
    return ProductFlowFocusView(
        active_workspace_id=focus.active_workspace_id,
        active_workspace_label=focus.active_workspace_label,
        active_right_panel_id=right_panel_id,
        active_right_panel_label=_panel_label(right_panel_id, app_language=app_language),
        active_bottom_panel_id=bottom_panel_id,
        active_bottom_panel_label=_panel_label(bottom_panel_id, app_language=app_language),
        recommended_action_id=focus.recommended_action_id,
        recommended_flow_id=focus.recommended_flow_id,
        focus_reason=reason,
    )




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
    if shell_vm is not None and shell_vm.diagnostics.beginner_mode and shell_vm.diagnostics.empty_workspace_mode:
        return "build"
    if shell_vm is not None and shell_vm.shell_mode in {"runtime_monitoring", "run_review"}:
        return "run"
    if shell_vm is not None and shell_vm.shell_mode == "designer_review":
        return "review"
    if workflow_hub is not None and workflow_hub.active_workflow_id == "execution_launch":
        return "run"
    if workflow_hub is not None and workflow_hub.active_workflow_id == "proposal_commit":
        return "review"
    if shell_vm is not None and shell_vm.shell_mode == "snapshot_review":
        if shell_vm.storage is not None and shell_vm.storage.commit_snapshot_card is not None and shell_vm.storage.commit_snapshot_card.can_execute:
            return "run"
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


def _requested_core_workspace_focus(selected_action_id: str | None, shell_vm: BuilderShellViewModel | None, *, app_language: str) -> ProductFlowFocusView | None:
    if shell_vm is None or selected_action_id is None:
        return None
    if selected_action_id == "open_visual_editor":
        right_panel_id = "inspector" if shell_vm.inspector is not None and shell_vm.inspector.object_type not in {"none", "unknown"} else "designer"
        bottom_panel_id = "diff" if shell_vm.diff is not None else ("validation" if shell_vm.validation is not None and (shell_vm.validation.summary.blocking_count or shell_vm.validation.summary.warning_count or shell_vm.validation.summary.confirmation_count) else "storage")
        return ProductFlowFocusView(active_workspace_id="visual_editor", active_workspace_label=_workspace_label("visual_editor", app_language=app_language), active_right_panel_id=right_panel_id, active_right_panel_label=_panel_label(right_panel_id, app_language=app_language), active_bottom_panel_id=bottom_panel_id, active_bottom_panel_label=_panel_label(bottom_panel_id, app_language=app_language), focus_reason="explicit_core_workspace_surface")
    if selected_action_id == "open_node_configuration":
        right_panel_id = shell_vm.coordination.active_panel if shell_vm.coordination.active_panel in {"designer", "validation", "inspector"} else ("inspector" if shell_vm.inspector is not None and shell_vm.inspector.object_type not in {"none", "unknown"} else "designer")
        bottom_panel_id = "diff" if shell_vm.diff is not None else ("validation" if shell_vm.validation is not None else "storage")
        return ProductFlowFocusView(active_workspace_id="node_configuration", active_workspace_label=_workspace_label("node_configuration", app_language=app_language), active_right_panel_id=right_panel_id, active_right_panel_label=_panel_label(right_panel_id, app_language=app_language), active_bottom_panel_id=bottom_panel_id, active_bottom_panel_label=_panel_label(bottom_panel_id, app_language=app_language), focus_reason="explicit_core_workspace_surface")
    if selected_action_id == "open_runtime_monitoring":
        bottom_panel_id = "trace_timeline" if shell_vm.trace_timeline is not None and shell_vm.trace_timeline.events else ("artifact" if shell_vm.artifact is not None and shell_vm.artifact.artifact_list else "storage")
        return ProductFlowFocusView(active_workspace_id="runtime_monitoring", active_workspace_label=_workspace_label("runtime_monitoring", app_language=app_language), active_right_panel_id="execution", active_right_panel_label=_panel_label("execution", app_language=app_language), active_bottom_panel_id=bottom_panel_id, active_bottom_panel_label=_panel_label(bottom_panel_id, app_language=app_language), focus_reason="explicit_core_workspace_surface")
    return None


def _focus(shell_vm: BuilderShellViewModel | None, stage_id: str, recommended_action_id: str | None, recommended_flow_id: str | None, *, app_language: str, source=None, execution_record=None, handoff: ProductFlowHandoffViewModel | None = None, selected_action_id: str | None = None) -> ProductFlowFocusView:
    if shell_vm is None:
        return ProductFlowFocusView()

    active_workspace_id = shell_vm.active_workspace_id
    focus_reason = "steady_state"
    explicit_panel = shell_vm.coordination.active_panel
    if explicit_panel in {"circuit_library", "feedback_channel"}:
        return _sanitize_focus_for_beginner_policy(shell_vm, ProductFlowFocusView(
            active_workspace_id="library",
            active_workspace_label=_workspace_label("library", app_language=app_language),
            active_right_panel_id=explicit_panel,
            active_right_panel_label=_panel_label(explicit_panel, app_language=app_language),
            active_bottom_panel_id="storage",
            active_bottom_panel_label=_panel_label("storage", app_language=app_language),
            recommended_action_id=recommended_action_id,
            recommended_flow_id=recommended_flow_id,
            focus_reason="explicit_return_use_surface",
        ), app_language=app_language)
    if explicit_panel == "result_history":
        return _sanitize_focus_for_beginner_policy(shell_vm, ProductFlowFocusView(
            active_workspace_id="runtime_monitoring",
            active_workspace_label=_workspace_label("runtime_monitoring", app_language=app_language),
            active_right_panel_id="result_history",
            active_right_panel_label=_panel_label("result_history", app_language=app_language),
            active_bottom_panel_id="execution",
            active_bottom_panel_label=_panel_label("execution", app_language=app_language),
            recommended_action_id=recommended_action_id,
            recommended_flow_id=recommended_flow_id,
            focus_reason="explicit_return_use_surface",
        ), app_language=app_language)
    explicit_core_focus = _requested_core_workspace_focus(selected_action_id, shell_vm, app_language=app_language)
    if explicit_core_focus is not None:
        return _sanitize_focus_for_beginner_policy(shell_vm, ProductFlowFocusView(active_workspace_id=explicit_core_focus.active_workspace_id, active_workspace_label=explicit_core_focus.active_workspace_label, active_right_panel_id=explicit_core_focus.active_right_panel_id, active_right_panel_label=explicit_core_focus.active_right_panel_label, active_bottom_panel_id=explicit_core_focus.active_bottom_panel_id, active_bottom_panel_label=explicit_core_focus.active_bottom_panel_label, recommended_action_id=recommended_action_id, recommended_flow_id=recommended_flow_id, focus_reason=explicit_core_focus.focus_reason), app_language=app_language)
    beginner_empty_designer = (
        shell_vm.diagnostics.beginner_mode
        and shell_vm.diagnostics.empty_workspace_mode
        and not shell_vm.diagnostics.advanced_surfaces_unlocked
    )
    beginner_surface = beginner_surface_active(source, execution_record)

    if stage_id == "run":
        active_workspace_id = "runtime_monitoring"
        if beginner_surface:
            active_right_panel_id = "execution"
            if shell_vm.execution is not None and shell_vm.execution.execution_status in {"running", "queued"}:
                active_bottom_panel_id = "trace_timeline" if shell_vm.trace_timeline is not None and shell_vm.trace_timeline.events else "artifact"
                focus_reason = "beginner_live_execution"
            else:
                active_bottom_panel_id = "storage"
                focus_reason = "read_result_first"
        elif shell_vm.execution is not None and shell_vm.execution.execution_status in {"running", "queued"}:
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
        if shell_vm.coordination.active_panel in {"circuit_library", "feedback_channel"}:
            active_workspace_id = "library"
            active_right_panel_id = shell_vm.coordination.active_panel
            active_bottom_panel_id = "storage"
            focus_reason = "return_use_surface"
        elif shell_vm.coordination.active_panel == "result_history":
            active_workspace_id = "runtime_monitoring"
            active_right_panel_id = "result_history"
            active_bottom_panel_id = "execution"
            focus_reason = "result_history_surface"
        else:
            active_workspace_id = "node_configuration" if beginner_empty_designer else "visual_editor"
            if shell_vm.coordination.active_panel in {"designer", "validation", "inspector"}:
                active_right_panel_id = shell_vm.coordination.active_panel
            elif shell_vm.inspector is not None and shell_vm.inspector.object_type not in {"none", "unknown"}:
                active_right_panel_id = "inspector"
            else:
                active_right_panel_id = "designer"
            if beginner_empty_designer:
                active_bottom_panel_id = "validation" if shell_vm.validation is not None and shell_vm.validation.summary.blocking_count else "storage"
                focus_reason = "start_with_goal"
            elif shell_vm.diff is not None:
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

    if not beginner_empty_designer and not (beginner_surface and active_workspace_id == "runtime_monitoring") and handoff is not None and handoff.primary_workspace_id is not None and handoff.primary_panel_id is not None:
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

    return _sanitize_focus_for_beginner_policy(shell_vm, ProductFlowFocusView(
        active_workspace_id=active_workspace_id,
        active_workspace_label=_workspace_label(active_workspace_id, app_language=app_language),
        active_right_panel_id=active_right_panel_id,
        active_right_panel_label=_panel_label(active_right_panel_id, app_language=app_language),
        active_bottom_panel_id=active_bottom_panel_id,
        active_bottom_panel_label=_panel_label(active_bottom_panel_id, app_language=app_language),
        recommended_action_id=recommended_action_id,
        recommended_flow_id=recommended_flow_id,
        focus_reason=focus_reason,
    ), app_language=app_language)


def _surface_targets(shell_vm: BuilderShellViewModel | None, *, app_language: str, focus: ProductFlowFocusView) -> tuple[list[ProductFlowSurfaceTargetView], list[ProductFlowSurfaceTargetView]]:
    if shell_vm is None:
        return [], []

    right_stack_ids = ["inspector", "designer", "validation", "execution", "trace_timeline", "artifact", "circuit_library", "result_history", "feedback_channel"]
    bottom_dock_ids = ["validation", "storage", "execution", "trace_timeline", "artifact", "diff", "result_history", "feedback_channel"]
    hidden_in_beginner = _suppressed_panel_ids(shell_vm)

    status_by_panel = {
        "inspector": "ready" if shell_vm.inspector is not None else "empty",
        "designer": shell_vm.designer.request_state.request_status if shell_vm.designer is not None else "empty",
        "validation": shell_vm.validation.overall_status if shell_vm.validation is not None else "empty",
        "storage": shell_vm.storage.lifecycle_summary.current_stage if shell_vm.storage is not None else "empty",
        "execution": shell_vm.execution.execution_status if shell_vm.execution is not None else "empty",
        "trace_timeline": shell_vm.trace_timeline.timeline_status if shell_vm.trace_timeline is not None else "empty",
        "artifact": shell_vm.artifact.viewer_status if shell_vm.artifact is not None else "empty",
        "diff": shell_vm.diff.viewer_status if shell_vm.diff is not None else "hidden",
        "circuit_library": shell_vm.circuit_library.library_status if shell_vm.circuit_library is not None else "empty",
        "result_history": shell_vm.result_history.history_status if shell_vm.result_history is not None else "empty",
        "feedback_channel": shell_vm.feedback_channel.channel_status if shell_vm.feedback_channel is not None else "empty",
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
        "circuit_library": "library",
        "result_history": "runtime_monitoring",
        "feedback_channel": "library",
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
        if panel_id not in hidden_in_beginner and (status_by_panel[panel_id] != "empty" or panel_id in {"inspector", "designer", "validation"})
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
        if panel_id not in hidden_in_beginner and (status_by_panel[panel_id] not in {"empty", "hidden"} or panel_id in {"validation", "storage"})
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
    selected_action_id: str | None = None,
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
        selected_action_id=selected_action_id,
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

    closure_vm = read_product_flow_closure_view_model(
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
        runbook=runbook_vm,
        handoff=handoff_vm,
        readiness=readiness_vm,
        e2e_path=e2e_path_vm,
        end_user_flow_hub=end_user_flow_hub,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    transition_vm = read_product_flow_transition_view_model(
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
        runbook=runbook_vm,
        handoff=handoff_vm,
        readiness=readiness_vm,
        e2e_path=e2e_path_vm,
        closure=closure_vm,
        end_user_flow_hub=end_user_flow_hub,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    gateway_vm = read_product_flow_gateway_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    e2e_proof_vm = read_product_flow_e2e_proof_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        proposal_commit=(workflow_hub.proposal_commit if workflow_hub is not None else None),
        execution_launch=(workflow_hub.execution_launch if workflow_hub is not None else None),
        end_user_flow_hub=end_user_flow_hub,
        gateway=gateway_vm,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    stage_id = _stage_id(shell_vm, workflow_hub)
    recommended_flow_id = end_user_flow_hub.recommended_flow_id if end_user_flow_hub is not None else None
    recommended_action_id = (transition_vm.next_action_id if transition_vm is not None else None) or (next((entry.action_id for entry in (runbook_vm.entries if runbook_vm is not None else []) if entry.entry_id == runbook_vm.recommended_entry_id and entry.action_id is not None), None) if runbook_vm is not None else None) or (execution_adapter_hub.recommended_action_id if execution_adapter_hub is not None else None)
    focus = _focus(shell_vm, stage_id, recommended_action_id, recommended_flow_id, app_language=app_language, source=source_unwrapped, execution_record=execution_record, handoff=handoff_vm, selected_action_id=selected_action_id)
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
    elif stage.blocking_count or (dispatch_hub is not None and dispatch_hub.hub_status == "blocked") or (execution_adapter_hub is not None and execution_adapter_hub.hub_status == "blocked"):
        shell_status = "blocked"
    elif stage.stage_id == "run" and stage.live_execution:
        shell_status = "live_run"
    elif storage_role == "execution_record" and stage.stage_id == "run" and not stage.live_execution:
        shell_status = "terminal"
    elif stage.stage_id == "review":
        shell_status = "review_focus"
    elif stage.stage_id == "build":
        shell_status = "build_focus"
    elif (workflow_hub is not None and workflow_hub.hub_status == "attention") or (dispatch_hub is not None and dispatch_hub.hub_status == "attention") or (execution_adapter_hub is not None and execution_adapter_hub.hub_status == "attention") or stage.warning_count or stage.pending_approval_count:
        shell_status = "attention"
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
        closure=closure_vm,
        transition=transition_vm,
        gateway=gateway_vm,
        e2e_proof=e2e_proof_vm,
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
