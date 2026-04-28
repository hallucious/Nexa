from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import Any

from src.contracts.nex_contract import ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.contracts.workspace_library_contract import (
    ProductActivityContinuitySummary,
    ProductWorkspaceLinks,
    ProductWorkspaceListResponse,
    ProductWorkspaceSummaryView,
)
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.inspector_panel import SelectedObjectViewModel, read_selected_object_view_model
from src.ui.i18n import beginner_ui_text, ui_language_from_sources, ui_text
from src.ui.beginner_surface_gate import beginner_locked_policy_surface_ids
from src.ui.beginner_milestones import beginner_advanced_surfaces_unlocked, build_beginner_first_success_completion_metadata_patch, explicit_beginner_first_success_achieved, return_use_ready, terminal_execution_record_view
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.top_bar import BuilderTopBarViewModel, read_builder_top_bar_view_model
from src.ui.command_palette import CommandPaletteViewModel, read_command_palette_view_model
from src.ui.execution_anxiety_reduction import (
    ContextualHelpView,
    MobileFirstRunView,
    PrivacyTransparencyView,
    read_contextual_help_view,
    read_mobile_first_run_view,
    read_privacy_transparency_view,
)
from src.ui.visual_editor_workspace import VisualEditorWorkspaceViewModel, read_visual_editor_workspace_view_model
from src.ui.runtime_monitoring_workspace import RuntimeMonitoringWorkspaceViewModel, read_runtime_monitoring_workspace_view_model
from src.ui.node_configuration_workspace import NodeConfigurationWorkspaceViewModel, read_node_configuration_workspace_view_model
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel, read_trace_timeline_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model
from src.ui.circuit_library import CircuitLibraryViewModel, read_circuit_library_view_model
from src.ui.result_history import ResultHistoryViewModel, read_result_history_view_model
from src.ui.feedback_channel import FeedbackChannelViewModel, read_feedback_channel_view_model


@dataclass(frozen=True)
class BuilderShellLayoutView:
    active_theme_id: str | None = None
    active_layout_id: str | None = None
    density_mode: str | None = None
    user_mode: str | None = None
    zoom_level: float | None = None
    viewport_center: dict[str, Any] = field(default_factory=dict)
    dock_mode: str | None = None


@dataclass(frozen=True)
class BuilderShellDiagnosticsView:
    warning_count: int = 0
    stale_selection_count: int = 0
    panel_coordination_warning: bool = False
    partial_panel_count: int = 0
    beginner_mode: bool = False
    empty_workspace_mode: bool = False
    advanced_surfaces_unlocked: bool = True
    explanation: str | None = None


@dataclass(frozen=True)
class BeginnerOnboardingHintView:
    visible: bool = False
    title: str | None = None
    summary: str | None = None
    primary_action_label: str | None = None
    primary_action_target: str | None = None


@dataclass(frozen=True)
class BeginnerSurfacePolicyView:
    visible: bool = False
    primary_surface_id: str | None = None
    primary_workspace_id: str | None = None
    suppressed_surface_ids: tuple[str, ...] = ()
    unlock_condition: str | None = None
    can_open_advanced_surfaces: bool = True
    graph_first_allowed: bool = True
    explanation: str | None = None


@dataclass(frozen=True)
class WorkspaceChainStageView:
    workspace_id: str = "visual_editor"
    workspace_label: str | None = None
    closure_state: str | None = None
    closure_label: str | None = None
    pending_barrier_count: int = 0
    blocking_barrier_count: int = 0
    dominant_barrier_kind: str | None = None
    summary: str | None = None
    recommended_action_id: str | None = None
    recommended_action_label: str | None = None


@dataclass(frozen=True)
class WorkspaceChainReviewView:
    chain_state: str = "hold_visual_editor"
    chain_label: str | None = None
    next_bottleneck_workspace: str | None = None
    next_bottleneck_label: str | None = None
    recommended_action_id: str | None = None
    recommended_action_label: str | None = None
    reopen_workspace_ids: tuple[str, ...] = ()
    stages: tuple[WorkspaceChainStageView, ...] = ()
    summary: str | None = None


@dataclass(frozen=True)
class ProductSurfaceStageView:
    stage_id: str
    stage_label: str | None = None
    stage_state: str = "inactive"
    stage_state_label: str | None = None
    blocker_count: int = 0
    pending_count: int = 0
    summary: str | None = None
    recommended_action_id: str | None = None
    recommended_action_label: str | None = None
    preferred_workspace_id: str | None = None
    preferred_panel_id: str | None = None


@dataclass(frozen=True)
class FirstSuccessPreflightBlockerView:
    family: str
    reason_code: str
    message: str
    next_action: str
    severity: str = "blocking"
    source_ref: str | None = None


@dataclass(frozen=True)
class FirstSuccessPreflightView:
    visible: bool = False
    ready: bool = True
    blocker_count: int = 0
    warning_count: int = 0
    top_family: str | None = None
    top_reason_code: str | None = None
    cause: str | None = None
    next_action: str | None = None
    estimated_total_cost_ratio: float | None = None
    blockers: tuple[FirstSuccessPreflightBlockerView, ...] = ()
    warnings: tuple[FirstSuccessPreflightBlockerView, ...] = ()


@dataclass(frozen=True)
class FirstSuccessStepView:
    step_id: str
    label: str | None = None
    state: str = "pending"
    summary: str | None = None
    recommended_action_id: str | None = None
    recommended_action_label: str | None = None
    preferred_workspace_id: str | None = None
    preferred_panel_id: str | None = None


@dataclass(frozen=True)
class FirstSuccessResultView:
    visible: bool = False
    state: str = "hidden"
    summary: str | None = None
    primary_text: str | None = None
    output_ref: str | None = None
    artifact_ref: str | None = None
    next_action_id: str | None = None
    next_action_label: str | None = None
    preferred_panel_id: str | None = None
    completion_action_id: str | None = None
    completion_action_label: str | None = None
    completion_metadata_patch: dict[str, Any] = field(default_factory=dict)
    read_complete: bool = False


@dataclass(frozen=True)
class FirstSuccessDesignerProposalView:
    visible: bool = False
    proposal_state: str = "hidden"
    summary: str | None = None
    next_action_id: str | None = None
    next_action_label: str | None = None
    preferred_panel_id: str | None = None
    preview_status: str | None = None
    approval_status: str | None = None
    commit_eligible: bool = False
    review_complete: bool = False


@dataclass(frozen=True)
class FirstSuccessFlowView:
    visible: bool = False
    flow_state: str = "hidden"
    current_step_id: str | None = None
    current_step_label: str | None = None
    summary: str | None = None
    next_action_id: str | None = None
    next_action_label: str | None = None
    preferred_workspace_id: str | None = None
    preferred_panel_id: str | None = None
    advanced_surfaces_unlocked: bool = True
    unlock_condition: str | None = None
    result_reading: FirstSuccessResultView = field(default_factory=FirstSuccessResultView)
    designer_proposal: FirstSuccessDesignerProposalView = field(default_factory=FirstSuccessDesignerProposalView)
    steps: tuple[FirstSuccessStepView, ...] = ()


@dataclass(frozen=True)
class ProductReadinessReviewView:
    review_state: str = "hold_first_success_setup"
    review_label: str | None = None
    next_bottleneck_stage: str | None = None
    next_bottleneck_label: str | None = None
    recommended_action_id: str | None = None
    recommended_action_label: str | None = None
    stages: tuple[ProductSurfaceStageView, ...] = ()
    summary: str | None = None




@dataclass(frozen=True)
class BuilderShellViewModel:
    shell_status: str = "ready"
    shell_status_label: str | None = None
    storage_role: str = "none"
    shell_mode: str = "builder"
    shell_mode_label: str | None = None
    active_workspace_id: str = "visual_editor"
    active_workspace_label: str | None = None
    top_bar: BuilderTopBarViewModel | None = None
    command_palette: CommandPaletteViewModel | None = None
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    graph: GraphWorkspaceViewModel | None = None
    inspector: SelectedObjectViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    storage: StoragePanelViewModel | None = None
    execution: ExecutionPanelViewModel | None = None
    trace_timeline: TraceTimelineViewerViewModel | None = None
    artifact: ArtifactViewerViewModel | None = None
    diff: DiffViewerViewModel | None = None
    designer: DesignerPanelViewModel | None = None
    visual_editor: VisualEditorWorkspaceViewModel | None = None
    runtime_monitoring: RuntimeMonitoringWorkspaceViewModel | None = None
    node_configuration: NodeConfigurationWorkspaceViewModel | None = None
    circuit_library: CircuitLibraryViewModel | None = None
    result_history: ResultHistoryViewModel | None = None
    feedback_channel: FeedbackChannelViewModel | None = None
    workspace_chain: WorkspaceChainReviewView = field(default_factory=WorkspaceChainReviewView)
    product_readiness: ProductReadinessReviewView = field(default_factory=ProductReadinessReviewView)
    first_success_preflight: FirstSuccessPreflightView = field(default_factory=FirstSuccessPreflightView)
    first_success_flow: FirstSuccessFlowView = field(default_factory=FirstSuccessFlowView)
    layout: BuilderShellLayoutView = field(default_factory=BuilderShellLayoutView)
    diagnostics: BuilderShellDiagnosticsView = field(default_factory=BuilderShellDiagnosticsView)
    beginner_onboarding: BeginnerOnboardingHintView = field(default_factory=BeginnerOnboardingHintView)
    beginner_surface_policy: BeginnerSurfacePolicyView = field(default_factory=BeginnerSurfacePolicyView)
    contextual_help: ContextualHelpView = field(default_factory=ContextualHelpView)
    privacy_transparency: PrivacyTransparencyView = field(default_factory=PrivacyTransparencyView)
    mobile_first_run: MobileFirstRunView = field(default_factory=MobileFirstRunView)
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


def _ui_metadata(source) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}


def _ui_layout(source) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.layout or {})
    return {}



def _workspace_identity(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None, *, execution_record: ExecutionRecordModel | None = None) -> tuple[str | None, str | None, str | None]:
    if isinstance(source, WorkingSaveModel):
        return source.meta.working_save_id or None, source.meta.name or source.meta.working_save_id or None, source.meta.updated_at or source.meta.created_at or (execution_record.meta.finished_at if execution_record is not None else None) or '1970-01-01T00:00:00Z'
    if isinstance(source, CommitSnapshotModel):
        workspace_id = source.meta.source_working_save_id or source.lineage.source_working_save_id or source.meta.commit_id or None
        return workspace_id, source.meta.name or workspace_id, source.meta.updated_at or source.meta.created_at or (execution_record.meta.finished_at if execution_record is not None else None) or '1970-01-01T00:00:00Z'
    record = execution_record if execution_record is not None else (source if isinstance(source, ExecutionRecordModel) else None)
    if isinstance(record, ExecutionRecordModel):
        workspace_id = record.source.working_save_id or record.source.commit_id or None
        return workspace_id, record.meta.title or workspace_id, record.meta.finished_at or record.meta.started_at or record.meta.created_at or None
    return None, None, None


def _synthetic_library_view(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None, *, execution_record: ExecutionRecordModel | None, app_language: str) -> CircuitLibraryViewModel | None:
    workspace_id, workspace_title, updated_at = _workspace_identity(source, execution_record=execution_record)
    if workspace_id is None or workspace_title is None or updated_at is None:
        return None
    latest_run_id = None
    last_result_status = None
    activity = None
    onboarding_state = None
    if isinstance(source, WorkingSaveModel):
        last_run = source.runtime.last_run or {}
        latest_run_id = str(last_run.get('run_id') or '').strip() or None
        last_result_status = str(last_run.get('status') or last_run.get('semantic_status') or '').strip() or None
        activity = ProductActivityContinuitySummary(
            recent_run_count=1 if latest_run_id is not None else 0,
            active_run_count=1 if execution_record is not None and execution_record.meta.status in {'running', 'queued'} else 0,
            latest_activity_at=updated_at,
            latest_run_id=latest_run_id,
        )
        metadata = dict(source.ui.metadata or {})
        onboarding_state = {
            'current_step': metadata.get('beginner_current_step') or metadata.get('onboarding_step') or ('read_result' if explicit_beginner_first_success_achieved(source) else 'enter_goal'),
            'first_success_achieved': explicit_beginner_first_success_achieved(source),
        }
    elif isinstance(execution_record, ExecutionRecordModel):
        latest_run_id = execution_record.meta.run_id
        last_result_status = execution_record.meta.status
        activity = ProductActivityContinuitySummary(
            recent_run_count=1,
            active_run_count=1 if execution_record.meta.status in {'running', 'queued'} else 0,
            latest_activity_at=updated_at,
            latest_run_id=latest_run_id,
        )
    summary = ProductWorkspaceSummaryView(
        workspace_id=workspace_id,
        title=workspace_title,
        role='owner',
        updated_at=updated_at,
        last_run_id=latest_run_id,
        last_result_status=last_result_status,
        activity_continuity=activity,
        links=ProductWorkspaceLinks(
            detail=f'/app/workspaces/{workspace_id}',
            runs=f'/app/workspaces/{workspace_id}/results',
            onboarding=f'/app/workspaces/{workspace_id}',
        ),
    )
    return read_circuit_library_view_model(
        ProductWorkspaceListResponse(returned_count=1, workspaces=(summary,)),
        app_language=app_language,
        onboarding_state_by_workspace_id={workspace_id: onboarding_state} if onboarding_state is not None else None,
    )


def _synthetic_result_history_view(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None, *, execution_record: ExecutionRecordModel | None, app_language: str) -> ResultHistoryViewModel | None:
    workspace_id, workspace_title, _updated_at = _workspace_identity(source, execution_record=execution_record)
    if workspace_id is None or workspace_title is None:
        return None
    runs = []
    result_rows_by_run_id: dict[str, object] = {}
    onboarding_state = None
    if isinstance(source, WorkingSaveModel):
        metadata = dict(source.ui.metadata or {})
        onboarding_state = {
            'current_step': metadata.get('beginner_current_step') or metadata.get('onboarding_step') or ('read_result' if explicit_beginner_first_success_achieved(source) else 'enter_goal'),
            'first_success_achieved': explicit_beginner_first_success_achieved(source),
        }
        last_run = source.runtime.last_run or {}
        run_id = str(last_run.get('run_id') or '').strip()
        if run_id:
            status_value = str(last_run.get('status') or last_run.get('semantic_status') or 'completed').strip().lower()
            status_family = 'active' if status_value in {'running', 'queued'} else ('terminal_partial' if status_value == 'partial' else ('terminal_failure' if status_value in {'failed', 'cancelled', 'error'} else 'terminal_success'))
            runs.append(SimpleNamespace(
                run_id=run_id,
                workspace_id=workspace_id,
                status_family=status_family,
                created_at=str(last_run.get('started_at') or source.meta.updated_at or source.meta.created_at or ''),
                updated_at=str(last_run.get('finished_at') or source.meta.updated_at or source.meta.created_at or ''),
                completed_at=str(last_run.get('finished_at') or source.meta.updated_at or source.meta.created_at or ''),
                result_state=status_value,
                result_summary=SimpleNamespace(title='Latest run result', description=str(last_run.get('summary') or 'Recent result details are available.')),
                source_artifact=None,
            ))
            result_rows_by_run_id[run_id] = SimpleNamespace(
                run_id=run_id,
                workspace_id=workspace_id,
                result_state='ready_partial' if status_family == 'terminal_partial' else ('ready_failure' if status_family == 'terminal_failure' else ('running' if status_family == 'active' else 'ready_success')),
                final_status=status_value,
                result_summary=SimpleNamespace(title='Latest run result', description=str(last_run.get('summary') or 'Recent result details are available.')),
                final_output=SimpleNamespace(output_key='answer', value_preview=str(last_run.get('output_preview') or '')),
                source_artifact=None,
                updated_at=str(last_run.get('finished_at') or source.meta.updated_at or source.meta.created_at or ''),
            )
    record = execution_record if execution_record is not None else (source if isinstance(source, ExecutionRecordModel) else None)
    if isinstance(record, ExecutionRecordModel):
        output_preview = None
        output_key = None
        if record.outputs.final_outputs:
            first_output = record.outputs.final_outputs[0]
            output_preview = str(first_output.value_payload if first_output.value_payload not in (None, '') else (first_output.value_summary or ''))
            output_key = first_output.output_ref.split('.')[-1] if first_output.output_ref else 'answer'
        status_value = record.meta.status.strip().lower()
        status_family = 'active' if status_value in {'running', 'queued'} else ('terminal_partial' if status_value == 'partial' else ('terminal_failure' if status_value in {'failed', 'cancelled', 'error'} else 'terminal_success'))
        runs = [SimpleNamespace(
            run_id=record.meta.run_id,
            workspace_id=workspace_id,
            status_family=status_family,
            created_at=record.meta.created_at,
            updated_at=record.meta.finished_at or record.meta.started_at,
            completed_at=record.meta.finished_at,
            result_state=status_value,
            result_summary=SimpleNamespace(title=record.outputs.output_summary or 'Latest run result', description=record.outputs.output_summary or 'Recent result details are available.'),
            source_artifact=None,
        )]
        result_rows_by_run_id = {
            record.meta.run_id: SimpleNamespace(
                run_id=record.meta.run_id,
                workspace_id=workspace_id,
                result_state='ready_partial' if status_family == 'terminal_partial' else ('ready_failure' if status_family == 'terminal_failure' else ('running' if status_family == 'active' else 'ready_success')),
                final_status=status_value,
                result_summary=SimpleNamespace(title=record.outputs.output_summary or 'Latest run result', description=record.outputs.output_summary or 'Recent result details are available.'),
                final_output=SimpleNamespace(output_key=output_key or 'answer', value_preview=output_preview or ''),
                source_artifact=None,
                updated_at=record.meta.finished_at or record.meta.started_at,
            )
        }
    response = SimpleNamespace(workspace_id=workspace_id, workspace_title=workspace_title, runs=tuple(runs))
    return read_result_history_view_model(response, result_rows_by_run_id=result_rows_by_run_id, app_language=app_language, selected_run_id=(runs[0].run_id if runs else None), onboarding_state=onboarding_state)


def _synthetic_feedback_channel_view(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | None, *, execution_record: ExecutionRecordModel | None, app_language: str) -> FeedbackChannelViewModel | None:
    workspace_id, workspace_title, _updated_at = _workspace_identity(source, execution_record=execution_record)
    if workspace_id is None or workspace_title is None:
        return None
    prefill_run_id = execution_record.meta.run_id if isinstance(execution_record, ExecutionRecordModel) else None
    prefill_surface = 'result_history' if prefill_run_id else 'workspace_shell'
    return read_feedback_channel_view_model(
        workspace_id=workspace_id,
        workspace_title=workspace_title,
        app_language=app_language,
        prefill_surface=prefill_surface,
        prefill_run_id=prefill_run_id,
    )

def _is_empty_working_save(source: WorkingSaveModel | None) -> bool:
    if not isinstance(source, WorkingSaveModel):
        return False
    return not source.circuit.nodes and not source.circuit.edges


def _advanced_surfaces_unlocked(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None, *, execution_vm: ExecutionPanelViewModel | None = None) -> bool:
    return beginner_advanced_surfaces_unlocked(source)


def _beginner_surface_policy(
    *,
    beginner_mode: bool,
    empty_workspace_mode: bool,
    active_workspace_id: str,
    validation_vm: ValidationPanelViewModel | None,
    execution_vm: ExecutionPanelViewModel | None,
    app_language: str,
) -> BeginnerSurfacePolicyView:
    if not beginner_mode:
        return BeginnerSurfacePolicyView(
            visible=False,
            primary_surface_id=None,
            primary_workspace_id=active_workspace_id,
            suppressed_surface_ids=(),
            unlock_condition="already_unlocked",
            can_open_advanced_surfaces=True,
            graph_first_allowed=True,
            explanation=ui_text(
                "beginner.surface_policy.unlocked.explanation",
                app_language=app_language,
                fallback_text="Advanced surfaces are available because the beginner gate is already crossed or explicitly requested.",
            ),
        )

    suppressed = list(beginner_locked_policy_surface_ids())
    graph_first_allowed = not empty_workspace_mode
    primary_surface_id = "node_configuration"
    explanation_key = "beginner.surface_policy.first_success.explanation"
    fallback_explanation = "Keep the beginner path focused on the next concrete step until the first successful run is complete."

    if empty_workspace_mode:
        primary_surface_id = "designer"
        suppressed.extend(["graph_workspace", "visual_editor"])
        explanation_key = "beginner.surface_policy.empty.explanation"
        fallback_explanation = "Start from the Designer input before exposing the graph or deeper inspection surfaces."
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        primary_surface_id = "validation"
        explanation_key = "beginner.surface_policy.blocked.explanation"
        fallback_explanation = "Show the blocking issue and one next action before exposing deeper debugging surfaces."
    elif execution_vm is not None and execution_vm.execution_status in {"running", "queued"}:
        primary_surface_id = "execution"
        explanation_key = "beginner.surface_policy.running.explanation"
        fallback_explanation = "Show execution progress while keeping trace, diff, and artifact inspection behind the beginner gate."

    return BeginnerSurfacePolicyView(
        visible=True,
        primary_surface_id=primary_surface_id,
        primary_workspace_id=active_workspace_id,
        suppressed_surface_ids=tuple(dict.fromkeys(suppressed)),
        unlock_condition="first_success_or_explicit_advanced_request",
        can_open_advanced_surfaces=False,
        graph_first_allowed=graph_first_allowed,
        explanation=ui_text(explanation_key, app_language=app_language, fallback_text=fallback_explanation),
    )


def _beginner_onboarding_hint(
    *,
    beginner_mode: bool,
    empty_workspace_mode: bool,
    validation_vm: ValidationPanelViewModel | None,
    designer_vm: DesignerPanelViewModel | None,
    execution_vm: ExecutionPanelViewModel | None,
    app_language: str,
) -> BeginnerOnboardingHintView:
    if not beginner_mode:
        return BeginnerOnboardingHintView()

    if empty_workspace_mode:
        return BeginnerOnboardingHintView(
            visible=True,
            title=ui_text("beginner.onboarding.start.title", app_language=app_language),
            summary=ui_text("beginner.onboarding.start.summary", app_language=app_language),
            primary_action_label=ui_text("beginner.onboarding.start.action", app_language=app_language),
            primary_action_target="designer",
        )

    if validation_vm is not None and validation_vm.beginner_summary.status_signal is not None:
        summary = validation_vm.beginner_summary
        if validation_vm.overall_status == "blocked":
            return BeginnerOnboardingHintView(
                visible=True,
                title=ui_text("beginner.onboarding.fix.title", app_language=app_language),
                summary=summary.cause,
                primary_action_label=summary.next_action_label,
                primary_action_target="validation",
            )
        if validation_vm.overall_status in {"pass", "pass_with_warnings", "confirmation_required"} and designer_vm is not None and (designer_vm.approval_state.current_stage not in {None, "idle", "not_started", "completed"} or designer_vm.preview_state.preview_status == "ready"):
            return BeginnerOnboardingHintView(
                visible=True,
                title=ui_text("beginner.onboarding.review.title", app_language=app_language),
                summary=designer_vm.preview_state.one_sentence_summary or ui_text("proposal.beginner.prompt", app_language=app_language),
                primary_action_label=ui_text("beginner.onboarding.review.action", app_language=app_language),
                primary_action_target="designer",
            )
        if validation_vm.overall_status in {"pass", "pass_with_warnings", "confirmation_required"} and execution_vm is not None:
            return BeginnerOnboardingHintView(
                visible=True,
                title=ui_text("beginner.onboarding.run.title", app_language=app_language),
                summary=summary.cause or ui_text("beginner.onboarding.run.summary", app_language=app_language),
                primary_action_label=summary.next_action_label or ui_text("beginner.onboarding.run.action", app_language=app_language),
                primary_action_target="execution",
            )

    return BeginnerOnboardingHintView()


def _selected_ref_from_graph(graph_view: GraphWorkspaceViewModel | None) -> str | None:
    if graph_view is None:
        return None
    if graph_view.selected_node_ids:
        return f"node:{graph_view.selected_node_ids[0]}"
    if graph_view.selected_edge_ids:
        return f"edge:{graph_view.selected_edge_ids[0]}"
    return None


def _workspace_chain_stage(*, workspace_id: str, workspace_label: str | None, closure_state: str | None, closure_label: str | None, pending_barrier_count: int, blocking_barrier_count: int, dominant_barrier_kind: str | None, summary: str | None, recommended_action_id: str | None, recommended_action_label: str | None) -> WorkspaceChainStageView:
    return WorkspaceChainStageView(
        workspace_id=workspace_id,
        workspace_label=workspace_label,
        closure_state=closure_state,
        closure_label=closure_label,
        pending_barrier_count=pending_barrier_count,
        blocking_barrier_count=blocking_barrier_count,
        dominant_barrier_kind=dominant_barrier_kind,
        summary=summary,
        recommended_action_id=recommended_action_id,
        recommended_action_label=recommended_action_label,
    )



def _workspace_chain_review(*, storage_role: str, shell_mode: str, visual_editor_vm: VisualEditorWorkspaceViewModel | None, node_configuration_vm: NodeConfigurationWorkspaceViewModel | None, runtime_monitoring_vm: RuntimeMonitoringWorkspaceViewModel | None, app_language: str) -> WorkspaceChainReviewView:
    visual_stage = _workspace_chain_stage(
        workspace_id="visual_editor",
        workspace_label=ui_text("workspace.visual_editor.name", app_language=app_language, fallback_text="Visual editor"),
        closure_state=getattr(getattr(visual_editor_vm, "closure_verdict", None), "closure_state", None),
        closure_label=getattr(getattr(visual_editor_vm, "closure_verdict", None), "closure_label", None),
        pending_barrier_count=getattr(getattr(visual_editor_vm, "closure_verdict", None), "pending_barrier_count", 0),
        blocking_barrier_count=getattr(getattr(visual_editor_vm, "closure_verdict", None), "blocking_barrier_count", 0),
        dominant_barrier_kind=getattr(getattr(visual_editor_vm, "closure_verdict", None), "dominant_barrier_kind", None),
        summary=getattr(getattr(visual_editor_vm, "closure_verdict", None), "summary", None),
        recommended_action_id="open_visual_editor",
        recommended_action_label=ui_text("builder.action.open_visual_editor", app_language=app_language, fallback_text="Open editor"),
    )
    node_stage = _workspace_chain_stage(
        workspace_id="node_configuration",
        workspace_label=ui_text("workspace.node_configuration.name", app_language=app_language, fallback_text="Node configuration"),
        closure_state=getattr(getattr(node_configuration_vm, "closure_verdict", None), "closure_state", None),
        closure_label=getattr(getattr(node_configuration_vm, "closure_verdict", None), "closure_label", None),
        pending_barrier_count=getattr(getattr(node_configuration_vm, "closure_verdict", None), "pending_barrier_count", 0),
        blocking_barrier_count=getattr(getattr(node_configuration_vm, "closure_verdict", None), "blocking_barrier_count", 0),
        dominant_barrier_kind=getattr(getattr(node_configuration_vm, "closure_verdict", None), "dominant_barrier_kind", None),
        summary=getattr(getattr(node_configuration_vm, "closure_verdict", None), "summary", None),
        recommended_action_id="open_node_configuration",
        recommended_action_label=ui_text("builder.action.open_node_configuration", app_language=app_language, fallback_text="Open step settings"),
    )
    runtime_stage = _workspace_chain_stage(
        workspace_id="runtime_monitoring",
        workspace_label=ui_text("workspace.runtime_monitoring.name", app_language=app_language, fallback_text="Runtime monitoring"),
        closure_state=getattr(getattr(runtime_monitoring_vm, "closure_verdict", None), "closure_state", None),
        closure_label=getattr(getattr(runtime_monitoring_vm, "closure_verdict", None), "closure_label", None),
        pending_barrier_count=getattr(getattr(runtime_monitoring_vm, "closure_verdict", None), "pending_barrier_count", 0),
        blocking_barrier_count=getattr(getattr(runtime_monitoring_vm, "closure_verdict", None), "blocking_barrier_count", 0),
        dominant_barrier_kind=getattr(getattr(runtime_monitoring_vm, "closure_verdict", None), "dominant_barrier_kind", None),
        summary=getattr(getattr(runtime_monitoring_vm, "closure_verdict", None), "summary", None),
        recommended_action_id="open_runtime_monitoring",
        recommended_action_label=ui_text("builder.action.open_runtime_monitoring", app_language=app_language, fallback_text="Open run monitor"),
    )
    stages = (visual_stage, node_stage, runtime_stage)

    runtime_is_primary_context = storage_role == "execution_record" or shell_mode in {"runtime_monitoring", "run_review"}

    if storage_role == "execution_record":
        if runtime_stage.closure_state == "workspace_chain_stable":
            chain_state = "workspace_chain_stable"
            bottleneck_stage = runtime_stage
            summary_key = "shell.workspace_chain.summary.workspace_chain_stable"
            fallback_summary = "The current visual editor → node configuration → runtime monitoring chain is provisionally stable. Choose the next true project bottleneck instead of polishing this chain further."
        else:
            chain_state = "hold_runtime_monitoring"
            bottleneck_stage = runtime_stage
            summary_key = "shell.workspace_chain.summary.hold_runtime_monitoring"
            fallback_summary = "The workspace chain is still being held by runtime monitoring. Resolve live execution or pending run review before treating the chain as stable."
    elif runtime_is_primary_context and (runtime_stage.blocking_barrier_count or runtime_stage.closure_state in {"hold_runtime_monitoring", "near_closed"}):
        chain_state = "hold_runtime_monitoring"
        bottleneck_stage = runtime_stage
        summary_key = "shell.workspace_chain.summary.hold_runtime_monitoring"
        fallback_summary = "The workspace chain is still being held by runtime monitoring. Resolve live execution or pending run review before treating the chain as stable."
    elif visual_stage.blocking_barrier_count or visual_stage.closure_state == "hold_visual_editor":
        chain_state = "hold_visual_editor"
        bottleneck_stage = visual_stage
        summary_key = "shell.workspace_chain.summary.hold_visual_editor"
        fallback_summary = "The workspace chain is still being held by the visual editor. Keep the current focus there before widening scope."
    elif node_stage.blocking_barrier_count or node_stage.closure_state == "hold_node_configuration":
        chain_state = "hold_node_configuration"
        bottleneck_stage = node_stage
        summary_key = "shell.workspace_chain.summary.hold_node_configuration"
        fallback_summary = "The workspace chain is still being held by node configuration. Finish the current configuration review or repair work before moving on."
    elif runtime_stage.blocking_barrier_count or runtime_stage.closure_state == "hold_runtime_monitoring":
        chain_state = "hold_runtime_monitoring"
        bottleneck_stage = runtime_stage
        summary_key = "shell.workspace_chain.summary.hold_runtime_monitoring"
        fallback_summary = "The workspace chain is still being held by runtime monitoring. Resolve live execution or pending run review before treating the chain as stable."
    elif runtime_stage.closure_state == "workspace_chain_stable" and node_stage.closure_state in {"ready_to_move_on", "near_closed", None} and visual_stage.closure_state in {"ready_to_move_on", "near_closed", None}:
        chain_state = "workspace_chain_stable"
        bottleneck_stage = runtime_stage
        summary_key = "shell.workspace_chain.summary.workspace_chain_stable"
        fallback_summary = "The current visual editor → node configuration → runtime monitoring chain is provisionally stable. Choose the next true project bottleneck instead of polishing this chain further."
    elif node_stage.closure_state == "near_closed":
        chain_state = "hold_node_configuration"
        bottleneck_stage = node_stage
        summary_key = "shell.workspace_chain.summary.hold_node_configuration"
        fallback_summary = "The workspace chain is still being held by node configuration. Finish the current configuration review or repair work before moving on."
    elif visual_stage.closure_state == "near_closed":
        chain_state = "hold_visual_editor"
        bottleneck_stage = visual_stage
        summary_key = "shell.workspace_chain.summary.hold_visual_editor"
        fallback_summary = "The workspace chain is still being held by the visual editor. Keep the current focus there before widening scope."
    elif runtime_stage.closure_state == "near_closed":
        chain_state = "hold_runtime_monitoring"
        bottleneck_stage = runtime_stage
        summary_key = "shell.workspace_chain.summary.hold_runtime_monitoring"
        fallback_summary = "The workspace chain is still being held by runtime monitoring. Resolve live execution or pending run review before treating the chain as stable."
    else:
        chain_state = "hold_visual_editor"
        bottleneck_stage = visual_stage
        summary_key = "shell.workspace_chain.summary.hold_visual_editor"
        fallback_summary = "The workspace chain is still being held by the visual editor. Keep the current focus there before widening scope."

    reopen_workspace_ids = tuple(stage.workspace_id for stage in stages if (stage.pending_barrier_count or stage.blocking_barrier_count) and stage.workspace_id != (bottleneck_stage.workspace_id if chain_state != "workspace_chain_stable" else ""))
    return WorkspaceChainReviewView(
        chain_state=chain_state,
        chain_label=ui_text(f"shell.workspace_chain.state.{chain_state}", app_language=app_language, fallback_text=chain_state.replace("_", " ")),
        next_bottleneck_workspace=None if chain_state == "workspace_chain_stable" else bottleneck_stage.workspace_id,
        next_bottleneck_label=None if chain_state == "workspace_chain_stable" else bottleneck_stage.workspace_label,
        recommended_action_id=None if chain_state == "workspace_chain_stable" else bottleneck_stage.recommended_action_id,
        recommended_action_label=None if chain_state == "workspace_chain_stable" else bottleneck_stage.recommended_action_label,
        reopen_workspace_ids=reopen_workspace_ids,
        stages=stages,
        summary=ui_text(summary_key, app_language=app_language, fallback_text=fallback_summary),
    )


def _payload_from_first_success_preflight(first_success_preflight: Any | None) -> dict[str, Any] | None:
    if first_success_preflight is None:
        return None
    if hasattr(first_success_preflight, "to_payload"):
        payload = first_success_preflight.to_payload()
    elif isinstance(first_success_preflight, dict):
        payload = dict(first_success_preflight)
    else:
        payload = {
            "ready": getattr(first_success_preflight, "ready", True),
            "blockers": getattr(first_success_preflight, "blockers", ()),
            "warnings": getattr(first_success_preflight, "warnings", ()),
            "estimated_total_cost_ratio": getattr(first_success_preflight, "estimated_total_cost_ratio", None),
        }
    return dict(payload)


def _blocker_payload(blocker: Any) -> dict[str, Any]:
    if hasattr(blocker, "to_payload"):
        return dict(blocker.to_payload())
    if isinstance(blocker, dict):
        return dict(blocker)
    return {
        "family": getattr(blocker, "family", ""),
        "reason_code": getattr(blocker, "reason_code", ""),
        "message": getattr(blocker, "message", ""),
        "next_action": getattr(blocker, "next_action", ""),
        "severity": getattr(blocker, "severity", "blocking"),
        "source_ref": getattr(blocker, "source_ref", None),
    }


def _first_success_preflight_view(first_success_preflight: Any | None) -> FirstSuccessPreflightView:
    payload = _payload_from_first_success_preflight(first_success_preflight)
    if payload is None:
        return FirstSuccessPreflightView()

    blockers: list[FirstSuccessPreflightBlockerView] = []
    for raw in payload.get("blockers") or ():
        item = _blocker_payload(raw)
        family = str(item.get("family") or "").strip()
        reason_code = str(item.get("reason_code") or "").strip()
        message = str(item.get("message") or "").strip()
        next_action = str(item.get("next_action") or "").strip()
        if not (family and reason_code and message and next_action):
            continue
        blockers.append(
            FirstSuccessPreflightBlockerView(
                family=family,
                reason_code=reason_code,
                message=message,
                next_action=next_action,
                severity=str(item.get("severity") or "blocking").strip() or "blocking",
                source_ref=(str(item.get("source_ref")) if item.get("source_ref") is not None else None),
            )
        )

    warnings: list[FirstSuccessPreflightBlockerView] = []
    for raw in payload.get("warnings") or ():
        item = _blocker_payload(raw)
        family = str(item.get("family") or "").strip()
        reason_code = str(item.get("reason_code") or "").strip()
        message = str(item.get("message") or "").strip()
        next_action = str(item.get("next_action") or "").strip()
        if not (family and reason_code and message and next_action):
            continue
        warnings.append(
            FirstSuccessPreflightBlockerView(
                family=family,
                reason_code=reason_code,
                message=message,
                next_action=next_action,
                severity=str(item.get("severity") or "warning").strip() or "warning",
                source_ref=(str(item.get("source_ref")) if item.get("source_ref") is not None else None),
            )
        )

    top = blockers[0] if blockers else (warnings[0] if warnings else None)
    estimated_total_cost_ratio = payload.get("estimated_total_cost_ratio")
    return FirstSuccessPreflightView(
        visible=True,
        ready=bool(payload.get("ready", not blockers)),
        blocker_count=len(blockers),
        warning_count=len(warnings),
        top_family=(top.family if top is not None else None),
        top_reason_code=(top.reason_code if top is not None else None),
        cause=(top.message if top is not None else None),
        next_action=(top.next_action if top is not None else None),
        estimated_total_cost_ratio=(float(estimated_total_cost_ratio) if isinstance(estimated_total_cost_ratio, (int, float)) else None),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def _first_success_preflight_action(preflight: FirstSuccessPreflightView, *, app_language: str) -> tuple[str | None, str | None]:
    family = preflight.top_family
    if family == "provider":
        return "open_provider_setup", preflight.next_action or ui_text("builder.action.open_provider_setup", app_language=app_language, fallback_text="Connect AI model")
    if family in {"file_upload", "file_extraction"}:
        return "open_file_input", preflight.next_action or ui_text("builder.action.open_file_input", app_language=app_language, fallback_text="Fix file input")
    if family:
        return "open_node_configuration", preflight.next_action or ui_text("builder.action.open_node_configuration", app_language=app_language, fallback_text="Open step settings")
    return None, None


def _product_stage(*, stage_id: str, stage_label: str | None, stage_state: str, blocker_count: int, pending_count: int, summary: str | None, recommended_action_id: str | None, recommended_action_label: str | None, preferred_workspace_id: str | None, preferred_panel_id: str | None, app_language: str) -> ProductSurfaceStageView:
    return ProductSurfaceStageView(
        stage_id=stage_id,
        stage_label=stage_label,
        stage_state=stage_state,
        stage_state_label=ui_text(f"shell.product_readiness.stage_state.{stage_state}", app_language=app_language, fallback_text=stage_state.replace("_", " ")),
        blocker_count=blocker_count,
        pending_count=pending_count,
        summary=summary,
        recommended_action_id=recommended_action_id,
        recommended_action_label=recommended_action_label,
        preferred_workspace_id=preferred_workspace_id,
        preferred_panel_id=preferred_panel_id,
    )


def _first_success_achieved(*, source, execution_record: ExecutionRecordModel | None, execution_vm: ExecutionPanelViewModel | None) -> bool:
    if isinstance(source, WorkingSaveModel):
        return explicit_beginner_first_success_achieved(source)
    return terminal_execution_record_view(source)


def _run_action_enabled(execution_vm: ExecutionPanelViewModel | None) -> bool:
    if execution_vm is None:
        return False
    if execution_vm.control_state.can_run:
        return True
    return any(action.action_id == "run" and action.enabled for action in execution_vm.control_state.available_actions)


def _product_readiness_review(*, source, execution_record: ExecutionRecordModel | None, beginner_mode: bool, empty_workspace_mode: bool, designer_vm: DesignerPanelViewModel | None, validation_vm: ValidationPanelViewModel | None, execution_vm: ExecutionPanelViewModel | None, circuit_library_vm: CircuitLibraryViewModel | None, result_history_vm: ResultHistoryViewModel | None, feedback_channel_vm: FeedbackChannelViewModel | None, contextual_help: ContextualHelpView, privacy_transparency: PrivacyTransparencyView, mobile_first_run: MobileFirstRunView, first_success_preflight: FirstSuccessPreflightView, app_language: str) -> ProductReadinessReviewView:
    first_success = _first_success_achieved(source=source, execution_record=execution_record, execution_vm=execution_vm)

    provider_setup_needed = bool(designer_vm is not None and designer_vm.provider_setup_guidance.visible and not designer_vm.provider_inline_key_entry.has_connected_provider)
    template_available = bool(designer_vm is not None and designer_vm.template_gallery.visible and designer_vm.template_gallery.templates)
    external_input_available = bool(designer_vm is not None and designer_vm.external_input_guidance.visible)

    if first_success:
        setup_state = "complete"
        setup_blockers = 0
        setup_pending = 0
        setup_summary = ui_text("shell.product_readiness.summary.entry_complete", app_language=app_language, fallback_text="The beginner entry path is already crossed. Reuse the existing workflow surfaces instead of reopening first-step setup.")
        setup_action_id = None
        setup_action_label = None
    elif provider_setup_needed:
        setup_state = "provider_setup_needed"
        setup_blockers = 1
        setup_pending = 0
        setup_summary = (designer_vm.provider_setup_guidance.summary if designer_vm is not None else None) or ui_text("shell.product_readiness.summary.provider_setup_needed", app_language=app_language, fallback_text="Connect an AI model before the first workflow can run successfully.")
        setup_action_id = "open_provider_setup"
        setup_action_label = ui_text("builder.action.open_provider_setup", app_language=app_language, fallback_text="Connect AI model")
    elif empty_workspace_mode:
        setup_state = "goal_entry_needed"
        setup_blockers = 0
        setup_pending = 1
        setup_summary = contextual_help.summary or ui_text("shell.product_readiness.summary.goal_entry_needed", app_language=app_language, fallback_text="Start from a goal, starter template, file, or web address so the first workflow shape exists.")
        setup_action_id = "browse_templates" if template_available else None
        setup_action_label = ui_text("phase6.help.start.templates" if template_available else "beginner.onboarding.start.action", app_language=app_language, fallback_text=("Browse templates" if template_available else "Open Designer"))
    elif template_available or external_input_available:
        setup_state = "entry_ready"
        setup_blockers = 0
        setup_pending = 0
        setup_summary = ui_text("shell.product_readiness.summary.entry_ready", app_language=app_language, fallback_text="Starter entry surfaces are available. You can continue from a template, file, URL, or direct goal entry.")
        setup_action_id = "browse_templates" if template_available else None
        setup_action_label = ui_text("phase6.help.start.templates" if template_available else "beginner.onboarding.start.action", app_language=app_language, fallback_text=("Browse templates" if template_available else "Open Designer"))
    else:
        setup_state = "ready"
        setup_blockers = 0
        setup_pending = 0
        setup_summary = ui_text("shell.product_readiness.summary.entry_ready", app_language=app_language, fallback_text="Starter entry surfaces are available. You can continue from a template, file, URL, or direct goal entry.")
        setup_action_id = None
        setup_action_label = None

    setup_stage = _product_stage(
        stage_id="first_success_setup",
        stage_label=ui_text("shell.product_readiness.stage.first_success_setup", app_language=app_language, fallback_text="First success setup"),
        stage_state=setup_state,
        blocker_count=setup_blockers,
        pending_count=setup_pending,
        summary=setup_summary,
        recommended_action_id=setup_action_id,
        recommended_action_label=setup_action_label,
        preferred_workspace_id="node_configuration" if beginner_mode else "visual_editor",
        preferred_panel_id="designer",
        app_language=app_language,
    )

    if first_success_preflight.visible and not first_success_preflight.ready:
        run_state = "fix_before_run"
        run_blockers = max(first_success_preflight.blocker_count, 1)
        run_pending = 0
        run_summary = first_success_preflight.cause or ui_text("shell.product_readiness.summary.first_success_preflight_blocked", app_language=app_language, fallback_text="Resolve the provider or file blocker before the first run can continue.")
        run_action_id, run_action_label = _first_success_preflight_action(first_success_preflight, app_language=app_language)
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        run_state = "fix_before_run"
        run_blockers = 1
        run_pending = 0
        run_summary = validation_vm.beginner_summary.cause or contextual_help.summary or ui_text("shell.product_readiness.summary.fix_before_run", app_language=app_language, fallback_text="Fix the blocking issue before the first run can continue.")
        run_action_id, run_action_label = _validation_beginner_action(validation_vm, app_language=app_language)
        if run_action_id is None:
            run_action_id = "open_node_configuration"
            run_action_label = ui_text("builder.action.open_node_configuration", app_language=app_language, fallback_text="Open step settings")
    elif execution_vm is not None and execution_vm.waiting_feedback.visible:
        run_state = "run_in_progress"
        run_blockers = 1
        run_pending = 0
        run_summary = execution_vm.waiting_feedback.summary or ui_text("shell.product_readiness.summary.run_in_progress", app_language=app_language, fallback_text="A run is still active. Keep monitoring it before treating the first-success path as settled.")
        run_action_id = "open_runtime_monitoring"
        run_action_label = ui_text("builder.action.open_runtime_monitoring", app_language=app_language, fallback_text="Open run monitor")
    elif execution_vm is not None and execution_vm.result_reading.visible and execution_vm.result_reading.state == "ready":
        run_state = "complete"
        run_blockers = 0
        run_pending = 0
        run_summary = execution_vm.result_reading.summary or ui_text("shell.product_readiness.summary.result_ready", app_language=app_language, fallback_text="A readable result is already available for the first-success path.")
        if first_success:
            run_action_id = "open_result_history" if result_history_vm is not None and result_history_vm.visible else None
            run_action_label = ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results") if run_action_id is not None else None
        else:
            run_action_id = "open_runtime_monitoring"
            run_action_label = ui_text("builder.action.open_runtime_monitoring", app_language=app_language, fallback_text="Read result")
    elif _run_action_enabled(execution_vm):
        run_state = "ready_to_run"
        run_blockers = 0
        run_pending = 1
        cost_summary = None
        if first_success_preflight.visible and first_success_preflight.estimated_total_cost_ratio is not None:
            cost_summary = ui_text(
                "shell.product_readiness.summary.first_success_cost_estimate",
                app_language=app_language,
                fallback_text=f"Estimated provider cost ratio: {first_success_preflight.estimated_total_cost_ratio:g}.",
            )
        run_summary = cost_summary or (execution_vm.cost_visibility.summary if execution_vm is not None and execution_vm.cost_visibility.visible and execution_vm.cost_visibility.summary else None) or ui_text("shell.product_readiness.summary.ready_to_run", app_language=app_language, fallback_text="The workflow is ready enough to run. Review the expected usage, then launch it and read the result.")
        run_action_id = "run_current"
        run_action_label = ui_text("builder.action.run_current", app_language=app_language, fallback_text="Run current")
    elif first_success:
        run_state = "complete"
        run_blockers = 0
        run_pending = 0
        run_summary = ui_text("shell.product_readiness.summary.result_ready", app_language=app_language, fallback_text="A readable result is already available for the first-success path.")
        run_action_id = None
        run_action_label = None
    else:
        run_state = "waiting"
        run_blockers = 0
        run_pending = 1
        run_summary = contextual_help.summary or ui_text("shell.product_readiness.summary.run_waiting", app_language=app_language, fallback_text="The run path is not active yet. Keep moving through review and approval until the run action becomes available.")
        run_action_id = None
        run_action_label = None

    if privacy_transparency.visible and privacy_transparency.requires_acknowledgement and run_state not in {"complete", "run_in_progress"}:
        run_pending = max(run_pending, 1)
        if privacy_transparency.summary:
            run_summary = f"{run_summary} {privacy_transparency.summary}" if run_summary else privacy_transparency.summary

    if mobile_first_run.visible and mobile_first_run.summary and run_state in {"ready_to_run", "waiting"}:
        run_summary = mobile_first_run.summary

    run_stage = _product_stage(
        stage_id="first_success_run",
        stage_label=ui_text("shell.product_readiness.stage.first_success_run", app_language=app_language, fallback_text="First success run"),
        stage_state=run_state,
        blocker_count=run_blockers,
        pending_count=run_pending,
        summary=run_summary,
        recommended_action_id=run_action_id,
        recommended_action_label=run_action_label,
        preferred_workspace_id=("runtime_monitoring" if run_action_id in {"run_current", "open_runtime_monitoring", "open_result_history"} else "node_configuration"),
        preferred_panel_id=(
            "execution"
            if run_action_id in {"run_current", "open_runtime_monitoring"}
            else ("result_history" if run_action_id == "open_result_history" else "designer")
        ),
        app_language=app_language,
    )

    return_use_unlocked = first_success or return_use_ready(source)
    has_history = bool(result_history_vm is not None and result_history_vm.visible and result_history_vm.returned_count > 0)
    has_library = bool(circuit_library_vm is not None and circuit_library_vm.visible)
    has_feedback = bool(feedback_channel_vm is not None and feedback_channel_vm.visible)

    if not return_use_unlocked:
        return_state = "inactive"
        return_blockers = 0
        return_pending = 0
        return_summary = ui_text("shell.product_readiness.summary.return_use_inactive", app_language=app_language, fallback_text="Return-use surfaces unlock after the first successful run and result reading path are established.")
        return_action_id = None
        return_action_label = None
    elif has_history and has_library and has_feedback:
        return_state = "complete"
        return_blockers = 0
        return_pending = 0
        return_summary = ui_text("shell.product_readiness.summary.return_use_ready", app_language=app_language, fallback_text="Library, recent results, and feedback routes are all available for return visits.")
        return_action_id = "open_circuit_library"
        return_action_label = ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library")
    elif has_library and has_feedback:
        return_state = "history_needed"
        return_blockers = 1
        return_pending = 0
        return_summary = (result_history_vm.empty_summary if result_history_vm is not None else None) or ui_text("shell.product_readiness.summary.history_needed", app_language=app_language, fallback_text="The return-use path still needs readable result history so people can reopen what happened last time without entering deep trace tooling.")
        return_action_id = "open_result_history"
        return_action_label = ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results")
    else:
        return_state = "return_use_ready"
        return_blockers = 0
        return_pending = 1
        return_summary = ui_text("shell.product_readiness.summary.return_use_ready", app_language=app_language, fallback_text="Library, recent results, and feedback routes are all available for return visits.")
        return_action_id = "open_circuit_library" if has_library else None
        return_action_label = ui_text("builder.action.open_circuit_library", app_language=app_language, fallback_text="Open workflow library") if return_action_id is not None else None

    return_stage = _product_stage(
        stage_id="return_use",
        stage_label=ui_text("shell.product_readiness.stage.return_use", app_language=app_language, fallback_text="Return use"),
        stage_state=return_state,
        blocker_count=return_blockers,
        pending_count=return_pending,
        summary=return_summary,
        recommended_action_id=return_action_id,
        recommended_action_label=return_action_label,
        preferred_workspace_id="library" if return_action_id in {"open_circuit_library", "open_feedback_channel"} else "runtime_monitoring",
        preferred_panel_id="circuit_library" if return_action_id == "open_circuit_library" else ("feedback_channel" if return_action_id == "open_feedback_channel" else "result_history"),
        app_language=app_language,
    )

    stages = (setup_stage, run_stage, return_stage)
    if run_stage.stage_state == "fix_before_run" and not empty_workspace_mode and not first_success:
        review_state = "hold_first_success_run"
        bottleneck_stage = run_stage
        summary_key = "shell.product_readiness.summary.hold_first_success_run"
        fallback_summary = "The next real product bottleneck is still inside the first-success run path. Finish review, run, and readable result follow-through before widening scope."
    elif setup_stage.blocker_count or setup_stage.stage_state in {"goal_entry_needed", "provider_setup_needed"}:
        review_state = "hold_first_success_setup"
        bottleneck_stage = setup_stage
        summary_key = "shell.product_readiness.summary.hold_first_success_setup"
        fallback_summary = "The next real product bottleneck is still inside the first-success setup path. Finish goal entry or provider setup before widening scope."
    elif (run_stage.blocker_count or run_stage.stage_state in {"ready_to_run", "run_in_progress", "fix_before_run", "waiting", "complete"}) and not first_success:
        review_state = "hold_first_success_run"
        bottleneck_stage = run_stage
        summary_key = "shell.product_readiness.summary.hold_first_success_run"
        fallback_summary = "The next real product bottleneck is still inside the first-success run path. Finish review, run, and readable result follow-through before widening scope."
    elif return_stage.blocker_count:
        review_state = "hold_return_use"
        bottleneck_stage = return_stage
        summary_key = "shell.product_readiness.summary.hold_return_use"
        fallback_summary = "The first-success path is healthy enough, but return-use is still the next product bottleneck. Strengthen library/result-history/feedback continuity before widening scope."
    else:
        review_state = "product_surface_stable"
        bottleneck_stage = return_stage
        summary_key = "shell.product_readiness.summary.product_surface_stable"
        fallback_summary = "The current beginner-first and return-use product surfaces are provisionally stable. Choose the next true project bottleneck instead of polishing these paths further."

    return ProductReadinessReviewView(
        review_state=review_state,
        review_label=ui_text(f"shell.product_readiness.state.{review_state}", app_language=app_language, fallback_text=review_state.replace("_", " ")),
        next_bottleneck_stage=None if review_state == "product_surface_stable" else bottleneck_stage.stage_id,
        next_bottleneck_label=None if review_state == "product_surface_stable" else bottleneck_stage.stage_label,
        recommended_action_id=None if review_state == "product_surface_stable" else bottleneck_stage.recommended_action_id,
        recommended_action_label=None if review_state == "product_surface_stable" else bottleneck_stage.recommended_action_label,
        stages=stages,
        summary=ui_text(summary_key, app_language=app_language, fallback_text=fallback_summary),
    )



def _first_success_step(
    *,
    step_id: str,
    label_key: str,
    fallback_label: str,
    state: str,
    summary: str | None,
    recommended_action_id: str | None,
    recommended_action_label: str | None,
    preferred_workspace_id: str | None,
    preferred_panel_id: str | None,
    app_language: str,
) -> FirstSuccessStepView:
    return FirstSuccessStepView(
        step_id=step_id,
        label=ui_text(label_key, app_language=app_language, fallback_text=fallback_label),
        state=state,
        summary=summary,
        recommended_action_id=recommended_action_id,
        recommended_action_label=recommended_action_label,
        preferred_workspace_id=preferred_workspace_id,
        preferred_panel_id=preferred_panel_id,
    )


def _validation_beginner_action(validation_vm: ValidationPanelViewModel | None, *, app_language: str) -> tuple[str | None, str | None]:
    if validation_vm is None:
        return None, None
    summary = validation_vm.beginner_summary
    if summary.next_action_type:
        if summary.next_action_type in {"focus_top_issue", "request_revision"}:
            action_id = "open_node_configuration"
        elif summary.next_action_type == "proceed_to_approval":
            action_id = "review_current"
        else:
            action_id = summary.next_action_type
        return action_id, summary.next_action_label
    return "open_node_configuration", ui_text(
        "builder.action.open_node_configuration",
        app_language=app_language,
        fallback_text="Open step settings",
    )


def _step_state(step_id: str, *, current_step_id: str | None, blocked_step_id: str | None, completed_steps: set[str]) -> str:
    if step_id in completed_steps:
        return "complete"
    if step_id == blocked_step_id:
        return "blocked"
    if step_id == current_step_id:
        return "current"
    return "pending"


def _first_success_result_reading_view(
    execution_vm: ExecutionPanelViewModel | None,
    *,
    first_success: bool,
    app_language: str,
) -> FirstSuccessResultView:
    if execution_vm is None or not execution_vm.result_reading.visible:
        if first_success:
            return FirstSuccessResultView(
                visible=True,
                state="complete",
                summary=ui_text(
                    "shell.first_success_flow.result.complete",
                    app_language=app_language,
                    fallback_text="The first result has already been read. Advanced surfaces are available.",
                ),
                next_action_id="open_result_history",
                next_action_label=ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results"),
                preferred_panel_id="result_history",
                read_complete=True,
            )
        return FirstSuccessResultView()

    result = execution_vm.result_reading
    ready = result.state == "ready"
    partial = result.state == "partial"
    view_state = "ready_to_read" if ready else ("partial" if partial else result.state or "available")
    completion_patch: dict[str, Any] = {}
    completion_action_id: str | None = None
    completion_action_label: str | None = None
    if ready and not first_success:
        completion_patch = build_beginner_first_success_completion_metadata_patch(
            run_id=execution_vm.run_identity.run_id,
            output_ref=result.output_ref,
            artifact_ref=result.artifact_ref,
        )
        completion_action_id = "mark_first_result_read"
        completion_action_label = ui_text(
            "builder.action.mark_first_result_read",
            app_language=app_language,
            fallback_text="Mark result as read",
        )

    return FirstSuccessResultView(
        visible=True,
        state=("complete" if first_success and ready else view_state),
        summary=result.summary,
        primary_text=result.primary_text,
        output_ref=result.output_ref,
        artifact_ref=result.artifact_ref,
        next_action_id=("open_result_history" if first_success and ready else "open_runtime_monitoring"),
        next_action_label=(
            ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results")
            if first_success and ready
            else ui_text("builder.action.open_runtime_monitoring", app_language=app_language, fallback_text="Read result")
        ),
        preferred_panel_id=("result_history" if first_success and ready else "execution"),
        completion_action_id=completion_action_id,
        completion_action_label=completion_action_label,
        completion_metadata_patch=completion_patch,
        read_complete=bool(first_success and ready),
    )


def _designer_first_success_proposal_view(
    designer_vm: DesignerPanelViewModel | None,
    *,
    app_language: str,
) -> FirstSuccessDesignerProposalView:
    if designer_vm is None:
        return FirstSuccessDesignerProposalView()

    request_status = designer_vm.request_state.request_status
    preview_status = designer_vm.preview_state.preview_status
    approval_status = designer_vm.approval_state.approval_status
    final_outcome = designer_vm.approval_state.final_outcome
    commit_eligible = bool(designer_vm.approval_state.commit_eligible)
    approved = (
        commit_eligible
        or final_outcome in {"approved", "approved_for_commit", "committed"}
        or approval_status in {"approved", "approved_for_commit", "committed"}
    )

    if approved:
        return FirstSuccessDesignerProposalView(
            visible=True,
            proposal_state="approved",
            summary=ui_text(
                "shell.first_success_flow.designer.approved",
                app_language=app_language,
                fallback_text="The workflow proposal is approved. Continue to the run step.",
            ),
            preferred_panel_id="designer",
            preview_status=preview_status,
            approval_status=approval_status,
            commit_eligible=commit_eligible,
            review_complete=True,
        )

    if preview_status == "ready":
        if designer_vm.approval_state.unanswered_decision_count > 0:
            summary = ui_text(
                "shell.first_success_flow.designer.decisions_required",
                app_language=app_language,
                fallback_text="Review the required Designer decision before running.",
            )
            label = ui_text(
                "designer.action.review_required_decision",
                app_language=app_language,
                fallback_text="Review decision",
            )
        else:
            summary = designer_vm.preview_state.one_sentence_summary or ui_text(
                "shell.first_success_flow.designer.preview_ready",
                app_language=app_language,
                fallback_text="Review the workflow preview before running.",
            )
            label = ui_text(
                "designer.action.approve_for_commit",
                app_language=app_language,
                fallback_text="Approve workflow",
            )
        return FirstSuccessDesignerProposalView(
            visible=True,
            proposal_state="awaiting_approval",
            summary=summary,
            next_action_id="approve_for_commit",
            next_action_label=label,
            preferred_panel_id="designer",
            preview_status=preview_status,
            approval_status=approval_status,
            commit_eligible=commit_eligible,
            review_complete=False,
        )

    if designer_vm.precheck_state.overall_status in {"blocked", "fail", "failed"}:
        return FirstSuccessDesignerProposalView(
            visible=True,
            proposal_state="precheck_blocked",
            summary=designer_vm.precheck_state.top_issue_label or ui_text(
                "shell.first_success_flow.designer.precheck_blocked",
                app_language=app_language,
                fallback_text="Fix the Designer precheck issue before previewing the workflow.",
            ),
            next_action_id="open_designer",
            next_action_label=ui_text("beginner.onboarding.start.action", app_language=app_language, fallback_text="Open Designer"),
            preferred_panel_id="designer",
            preview_status=preview_status,
            approval_status=approval_status,
            commit_eligible=commit_eligible,
            review_complete=False,
        )

    if (
        request_status in {"submitted", "editing"}
        or designer_vm.intent_state.intent_id
        or designer_vm.patch_state.patch_id
        or designer_vm.precheck_state.precheck_id
    ):
        return FirstSuccessDesignerProposalView(
            visible=True,
            proposal_state="preparing_preview",
            summary=ui_text(
                "shell.first_success_flow.designer.preparing_preview",
                app_language=app_language,
                fallback_text="Nexa is preparing a workflow preview. Review it before running.",
            ),
            next_action_id="open_designer",
            next_action_label=ui_text("beginner.onboarding.start.action", app_language=app_language, fallback_text="Open Designer"),
            preferred_panel_id="designer",
            preview_status=preview_status,
            approval_status=approval_status,
            commit_eligible=commit_eligible,
            review_complete=False,
        )

    return FirstSuccessDesignerProposalView(
        preview_status=preview_status,
        approval_status=approval_status,
        commit_eligible=commit_eligible,
    )


def _first_success_flow_review(
    *,
    source,
    execution_record: ExecutionRecordModel | None,
    beginner_mode: bool,
    empty_workspace_mode: bool,
    advanced_unlocked: bool,
    designer_vm: DesignerPanelViewModel | None,
    validation_vm: ValidationPanelViewModel | None,
    execution_vm: ExecutionPanelViewModel | None,
    first_success_preflight: FirstSuccessPreflightView,
    product_readiness: ProductReadinessReviewView,
    app_language: str,
) -> FirstSuccessFlowView:
    first_success = _first_success_achieved(
        source=source,
        execution_record=execution_record,
        execution_vm=execution_vm,
    )
    should_show = bool(first_success or beginner_mode or product_readiness.review_state.startswith("hold_first_success"))
    if not should_show:
        return FirstSuccessFlowView(advanced_surfaces_unlocked=advanced_unlocked, unlock_condition="already_unlocked")

    completed_steps: set[str] = set()
    blocked_step_id: str | None = None
    current_step_id: str | None = None
    summary: str | None = None
    next_action_id: str | None = None
    next_action_label: str | None = None
    preferred_workspace_id: str | None = None
    preferred_panel_id: str | None = None
    flow_state = "in_progress"
    designer_proposal = _designer_first_success_proposal_view(designer_vm, app_language=app_language)
    result_reading = _first_success_result_reading_view(
        execution_vm,
        first_success=first_success,
        app_language=app_language,
    )

    if first_success:
        completed_steps = {"describe_goal", "review_workflow", "run_workflow", "read_result"}
        flow_state = "complete"
        summary = ui_text(
            "shell.first_success_flow.summary.complete",
            app_language=app_language,
            fallback_text="The first workflow has already reached a readable result. Advanced surfaces can now be opened.",
        )
        next_action_id = "open_result_history"
        next_action_label = ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results")
        preferred_workspace_id = "runtime_monitoring"
        preferred_panel_id = "result_history"
    elif empty_workspace_mode:
        current_step_id = "describe_goal"
        summary = (
            designer_vm.request_state.input_placeholder
            if designer_vm is not None and designer_vm.request_state.input_placeholder
            else ui_text(
                "shell.first_success_flow.summary.describe_goal",
                app_language=app_language,
                fallback_text="Describe what you want to build. Nexa will show a preview before anything is committed.",
            )
        )
        next_action_id = "open_designer"
        next_action_label = ui_text("beginner.onboarding.start.action", app_language=app_language, fallback_text="Open Designer")
        preferred_workspace_id = "node_configuration"
        preferred_panel_id = "designer"
    elif first_success_preflight.visible and not first_success_preflight.ready:
        blocked_step_id = "run_workflow"
        current_step_id = "run_workflow"
        summary = first_success_preflight.cause or ui_text(
            "shell.first_success_flow.summary.preflight_blocked",
            app_language=app_language,
            fallback_text="Resolve the provider or file blocker before running.",
        )
        next_action_id, next_action_label = _first_success_preflight_action(first_success_preflight, app_language=app_language)
        preferred_workspace_id = "node_configuration"
        preferred_panel_id = "designer" if next_action_id in {"open_provider_setup", "open_file_input"} else "validation"
        completed_steps = {"describe_goal", "review_workflow"}
        flow_state = "blocked"
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        blocked_step_id = "review_workflow"
        current_step_id = "review_workflow"
        summary = validation_vm.beginner_summary.cause or ui_text(
            "shell.first_success_flow.summary.validation_blocked",
            app_language=app_language,
            fallback_text="Fix the blocking workflow issue before running.",
        )
        next_action_id, next_action_label = _validation_beginner_action(validation_vm, app_language=app_language)
        preferred_workspace_id = "node_configuration"
        preferred_panel_id = "validation"
        completed_steps = {"describe_goal"}
        flow_state = "blocked"
    elif designer_proposal.visible and not designer_proposal.review_complete:
        blocked_step_id = "review_workflow" if designer_proposal.proposal_state in {"precheck_blocked", "awaiting_approval"} else None
        current_step_id = "review_workflow"
        summary = designer_proposal.summary or ui_text(
            "shell.first_success_flow.summary.review_designer_proposal",
            app_language=app_language,
            fallback_text="Review the Designer proposal before running.",
        )
        next_action_id = designer_proposal.next_action_id or "open_designer"
        next_action_label = designer_proposal.next_action_label or ui_text("beginner.onboarding.start.action", app_language=app_language, fallback_text="Open Designer")
        preferred_workspace_id = "node_configuration"
        preferred_panel_id = designer_proposal.preferred_panel_id or "designer"
        completed_steps = {"describe_goal"}
        flow_state = "blocked" if blocked_step_id is not None else "in_progress"
    elif execution_vm is not None and execution_vm.waiting_feedback.visible:
        current_step_id = "run_workflow"
        summary = execution_vm.waiting_feedback.summary or ui_text(
            "shell.first_success_flow.summary.run_in_progress",
            app_language=app_language,
            fallback_text="The run is in progress. Keep the run monitor open until a result is ready.",
        )
        next_action_id = "open_runtime_monitoring"
        next_action_label = ui_text("builder.action.open_runtime_monitoring", app_language=app_language, fallback_text="Open run monitor")
        preferred_workspace_id = "runtime_monitoring"
        preferred_panel_id = "execution"
        completed_steps = {"describe_goal", "review_workflow"}
        flow_state = "running"
    elif execution_vm is not None and execution_vm.result_reading.visible and execution_vm.result_reading.state == "ready":
        current_step_id = "read_result"
        summary = execution_vm.result_reading.summary or ui_text(
            "shell.first_success_flow.summary.read_result",
            app_language=app_language,
            fallback_text="A result is ready. Read it before unlocking deeper inspection surfaces.",
        )
        next_action_id = "open_runtime_monitoring"
        next_action_label = ui_text("builder.action.open_runtime_monitoring", app_language=app_language, fallback_text="Read result")
        preferred_workspace_id = "runtime_monitoring"
        preferred_panel_id = "execution"
        completed_steps = {"describe_goal", "review_workflow", "run_workflow"}
    elif _run_action_enabled(execution_vm):
        current_step_id = "run_workflow"
        summary = ui_text(
            "shell.first_success_flow.summary.ready_to_run",
            app_language=app_language,
            fallback_text="The workflow is ready enough to run. Launch it, then read the result.",
        )
        next_action_id = "run_current"
        next_action_label = ui_text("builder.action.run_current", app_language=app_language, fallback_text="Run current")
        preferred_workspace_id = "runtime_monitoring"
        preferred_panel_id = "execution"
        completed_steps = {"describe_goal", "review_workflow"}
    else:
        current_step_id = "review_workflow"
        summary = (
            validation_vm.beginner_summary.cause
            if validation_vm is not None and validation_vm.beginner_summary.cause
            else ui_text(
                "shell.first_success_flow.summary.review_workflow",
                app_language=app_language,
                fallback_text="Review the workflow preview and fix any simple validation issue before running.",
            )
        )
        next_action_id = "open_node_configuration"
        next_action_label = ui_text("builder.action.open_node_configuration", app_language=app_language, fallback_text="Open step settings")
        preferred_workspace_id = "node_configuration"
        preferred_panel_id = "validation"
        completed_steps = {"describe_goal"}

    step_defs = (
        ("describe_goal", "shell.first_success_flow.step.describe_goal", "Describe goal"),
        ("review_workflow", "shell.first_success_flow.step.review_workflow", "Review workflow"),
        ("run_workflow", "shell.first_success_flow.step.run_workflow", "Run workflow"),
        ("read_result", "shell.first_success_flow.step.read_result", "Read result"),
    )
    steps = tuple(
        _first_success_step(
            step_id=step_id,
            label_key=label_key,
            fallback_label=fallback_label,
            state=_step_state(step_id, current_step_id=current_step_id, blocked_step_id=blocked_step_id, completed_steps=completed_steps),
            summary=summary if step_id == current_step_id or step_id == blocked_step_id else None,
            recommended_action_id=next_action_id if step_id == current_step_id or step_id == blocked_step_id else None,
            recommended_action_label=next_action_label if step_id == current_step_id or step_id == blocked_step_id else None,
            preferred_workspace_id=preferred_workspace_id if step_id == current_step_id or step_id == blocked_step_id else None,
            preferred_panel_id=preferred_panel_id if step_id == current_step_id or step_id == blocked_step_id else None,
            app_language=app_language,
        )
        for step_id, label_key, fallback_label in step_defs
    )
    current_step = next((step for step in steps if step.step_id == current_step_id), None)
    return FirstSuccessFlowView(
        visible=True,
        flow_state=flow_state,
        current_step_id=current_step_id,
        current_step_label=current_step.label if current_step is not None else None,
        summary=summary,
        next_action_id=next_action_id,
        next_action_label=next_action_label,
        preferred_workspace_id=preferred_workspace_id,
        preferred_panel_id=preferred_panel_id,
        advanced_surfaces_unlocked=advanced_unlocked,
        unlock_condition="already_unlocked" if advanced_unlocked else "first_success_or_explicit_advanced_request",
        result_reading=result_reading,
        designer_proposal=designer_proposal,
        steps=steps,
    )


def _selected_ref_from_validation(validation_report: ValidationReport | None) -> str | None:
    if validation_report is None:
        return None
    ordered = sorted(
        list(validation_report.findings),
        key=lambda finding: (
            0 if finding.blocking else 1,
            0 if (finding.severity or "") == "high" else 1,
        ),
    )
    for finding in ordered:
        location = str(finding.location or "")
        if location.startswith(("node:", "edge:", "output:", "group:", "subcircuit:")):
            return location
        if location:
            return location
    return None




def _explicit_panel_id_for_workspace_action(selected_action_id: str | None, *, shell_vm_inputs: dict[str, object] | None = None) -> str | None:
    if selected_action_id == "open_visual_editor":
        return "graph"
    if selected_action_id == "open_runtime_monitoring":
        return "execution"
    if selected_action_id == "open_node_configuration":
        shell_vm_inputs = shell_vm_inputs or {}
        inspector_vm = shell_vm_inputs.get("inspector_vm")
        designer_vm = shell_vm_inputs.get("designer_vm")
        validation_vm = shell_vm_inputs.get("validation_vm")
        if inspector_vm is not None and getattr(inspector_vm, "object_type", "none") not in {"none", "unknown"}:
            return "inspector"
        if validation_vm is not None and getattr(validation_vm, "overall_status", None) == "blocked":
            return "validation"
        if designer_vm is not None:
            return "designer"
        return "inspector"
    return None


def _coordination_with_explicit_workspace_focus(coordination_vm: BuilderPanelCoordinationStateView, *, selected_action_id: str | None, shell_vm_inputs: dict[str, object] | None = None) -> BuilderPanelCoordinationStateView:
    panel_id = _explicit_panel_id_for_workspace_action(selected_action_id, shell_vm_inputs=shell_vm_inputs)
    if panel_id is None:
        return coordination_vm
    visible_panels = list(coordination_vm.visible_panels)
    if panel_id not in visible_panels:
        visible_panels.append(panel_id)
    panel_order = [panel_id, *[existing for existing in coordination_vm.panel_order if existing != panel_id]]
    return replace(coordination_vm, active_panel=panel_id, visible_panels=visible_panels, panel_order=panel_order, focus_mode="workspace_navigation")
def _requested_workspace_id_from_action(selected_action_id: str | None, *, action_schema: BuilderActionSchemaView) -> str | None:
    if not selected_action_id:
        return None
    mapping = {
        "open_visual_editor": "visual_editor",
        "open_node_configuration": "node_configuration",
        "open_runtime_monitoring": "runtime_monitoring",
    }
    workspace_id = mapping.get(selected_action_id)
    if workspace_id is None:
        return None
    actions = [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    for action in actions:
        if action.action_id == selected_action_id and action.enabled:
            return workspace_id
    return None


def read_builder_shell_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
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
    session_keys: dict | None = None,
    app_language: str | None = None,
    selected_action_id: str | None = None,
    first_success_preflight=None,
) -> BuilderShellViewModel:
    source_unwrapped = _unwrap(source)
    role = _storage_role(source_unwrapped)
    app_language = app_language or ui_language_from_sources(source_unwrapped, execution_record)

    graph_vm = read_graph_view_model(
        source,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
    ) if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel)) else None
    resolved_selected_ref = selected_ref or _selected_ref_from_graph(graph_vm) or _selected_ref_from_validation(validation_report)

    storage_vm = read_storage_view_model(
        source_unwrapped,
        latest_execution_record=(execution_record if execution_record is not None and not isinstance(source_unwrapped, ExecutionRecordModel) else None),
    ) if source_unwrapped is not None else None
    execution_vm = read_execution_panel_view_model(source_unwrapped, execution_record=execution_record, live_events=live_events) if source_unwrapped is not None else None
    trace_vm = read_trace_timeline_view_model(source_unwrapped if isinstance(source_unwrapped, ExecutionRecordModel) else source_unwrapped, execution_record=execution_record, live_events=live_events) if (source_unwrapped is not None or execution_record is not None) else None
    artifact_vm = read_artifact_viewer_view_model(source_unwrapped if source_unwrapped is not None else execution_record, execution_record=execution_record, selected_artifact_id=selected_artifact_id) if (source_unwrapped is not None or execution_record is not None) else None
    inspector_vm = read_selected_object_view_model(source_unwrapped, selected_ref=resolved_selected_ref, validation_report=validation_report, execution_record=execution_record, preview_overlay=preview_overlay) if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel)) else None
    validation_vm = read_validation_panel_view_model(source_unwrapped, validation_report=validation_report, precheck=precheck, execution_record=execution_record) if source_unwrapped is not None else None
    # Merge caller-supplied session_keys with any keys already stored in the
    # working save UI metadata.  Caller-supplied keys take priority so the UI
    # can inject a freshly-pasted key without overwriting existing metadata.
    effective_session_keys: dict = {}
    if isinstance(source_unwrapped, WorkingSaveModel):
        metadata_keys = {
            k: v
            for k, v in (source_unwrapped.ui.metadata or {}).get("provider_session_keys", {}).items()
            if isinstance(k, str) and isinstance(v, str) and v.strip()
        }
        effective_session_keys.update(metadata_keys)
    if session_keys:
        effective_session_keys.update(
            {k: v for k, v in session_keys.items() if isinstance(k, str) and isinstance(v, str) and v.strip()}
        )

    designer_vm = read_designer_panel_view_model(
        source_unwrapped,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
        session_keys=effective_session_keys or None,
    ) if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel)) else None

    diff_vm = None
    if diff_mode and diff_source is not None and diff_target is not None:
        diff_vm = read_diff_view_model(diff_mode=diff_mode, source=diff_source, target=diff_target)
    elif preview_overlay is not None and source_unwrapped is not None:
        diff_vm = read_diff_view_model(diff_mode="preview_vs_current", source=preview_overlay, target=source_unwrapped)
    elif isinstance(source_unwrapped, WorkingSaveModel) and storage_vm is not None and storage_vm.commit_snapshot_card is not None and storage_vm.commit_snapshot_card.commit_id is not None:
        # default shell comparison is only available when explicit commit target is supplied later.
        diff_vm = None

    circuit_library_vm = _synthetic_library_view(source_unwrapped, execution_record=execution_record, app_language=app_language)
    result_history_vm = _synthetic_result_history_view(source_unwrapped, execution_record=execution_record, app_language=app_language)
    feedback_channel_vm = _synthetic_feedback_channel_view(source_unwrapped, execution_record=execution_record, app_language=app_language)

    coordination_vm = read_panel_coordination_state(
        source_unwrapped,
        graph_view=graph_vm,
        storage_view=storage_vm,
        diff_view=diff_vm,
        execution_view=execution_vm,
        validation_view=validation_vm,
        designer_view=designer_vm,
        trace_view=trace_vm,
        artifact_view=artifact_vm,
        circuit_library_view=circuit_library_vm,
        result_history_view=result_history_vm,
        feedback_channel_view=feedback_channel_vm,
    )
    action_schema = read_builder_action_schema(
        source_unwrapped,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        designer_view=designer_vm,
        app_language=app_language,
    )

    coordination_vm = _coordination_with_explicit_workspace_focus(
        coordination_vm,
        selected_action_id=selected_action_id,
        shell_vm_inputs={
            "inspector_vm": inspector_vm,
            "designer_vm": designer_vm,
            "validation_vm": validation_vm,
        },
    )

    metadata = _ui_metadata(source_unwrapped)
    layout = _ui_layout(source_unwrapped)
    layout_vm = BuilderShellLayoutView(
        active_theme_id=str(metadata.get("active_theme_id")) if metadata.get("active_theme_id") is not None else None,
        active_layout_id=str(metadata.get("active_layout_id")) if metadata.get("active_layout_id") is not None else None,
        density_mode=str(metadata.get("density_mode")) if metadata.get("density_mode") is not None else None,
        user_mode=str(metadata.get("user_mode")) if metadata.get("user_mode") is not None else None,
        zoom_level=float(metadata.get("zoom_level")) if isinstance(metadata.get("zoom_level"), (int, float)) else None,
        viewport_center=dict(layout.get("viewport_center") or {}),
        dock_mode=str(metadata.get("dock_mode")) if metadata.get("dock_mode") is not None else None,
    )

    warning_count = 0
    partial_panel_count = 0
    for vm in [diff_vm, artifact_vm, trace_vm]:
        if vm is not None and getattr(vm, "viewer_status", None) == "partial":
            partial_panel_count += 1
    if validation_vm is not None:
        warning_count += validation_vm.summary.warning_count + validation_vm.summary.confirmation_count
    if storage_vm is not None:
        warning_count += storage_vm.diagnostics.lifecycle_warning_count

    shell_mode = "builder"
    if execution_vm is not None and execution_vm.execution_status in {"running", "queued"}:
        shell_mode = "runtime_monitoring"
    elif designer_vm is not None and designer_vm.request_state.request_status in {"submitted", "editing"}:
        shell_mode = "designer_review"
    elif role == "working_save":
        shell_mode = "draft_edit"
    elif role == "commit_snapshot":
        shell_mode = "snapshot_review"
    elif role == "execution_record":
        shell_mode = "run_review"

    visual_editor_vm = read_visual_editor_workspace_view_model(
        source_unwrapped,
        validation_report=validation_report,
        preview_overlay=preview_overlay,
        diff_mode=diff_mode,
        diff_source=diff_source,
        diff_target=diff_target,
    ) if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel)) else None

    runtime_monitoring_vm = read_runtime_monitoring_workspace_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        live_events=live_events,
        selected_artifact_id=selected_artifact_id,
    ) if (source_unwrapped is not None or execution_record is not None) else None

    node_configuration_vm = read_node_configuration_workspace_view_model(
        source_unwrapped,
        selected_ref=resolved_selected_ref,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        session_state_card=session_state_card,
        intent=intent,
        patch_plan=patch_plan,
        precheck=precheck,
        preview=preview,
        approval_flow=approval_flow,
    ) if isinstance(source_unwrapped, (WorkingSaveModel, CommitSnapshotModel)) else None

    empty_workspace_mode = _is_empty_working_save(source_unwrapped)
    advanced_unlocked = _advanced_surfaces_unlocked(source_unwrapped, execution_vm=execution_vm)
    beginner_mode = role == "working_save" and not advanced_unlocked
    diagnostics = BuilderShellDiagnosticsView(
        warning_count=warning_count,
        stale_selection_count=coordination_vm.stale_reference_count,
        panel_coordination_warning=coordination_vm.active_panel not in coordination_vm.visible_panels,
        partial_panel_count=partial_panel_count,
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        advanced_surfaces_unlocked=advanced_unlocked,
    )
    shell_status = "ready"
    if source_unwrapped is None:
        shell_status = "failed"
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        shell_status = "blocked"
    elif execution_vm is not None and execution_vm.execution_status in {"running", "queued"}:
        shell_status = "active"
    elif role == "execution_record" and execution_vm is not None and execution_vm.execution_status in {"completed", "failed", "cancelled", "partial", "idle"} and not diagnostics.panel_coordination_warning and warning_count == 0:
        shell_status = "terminal"
    elif diagnostics.panel_coordination_warning or warning_count > 0:
        shell_status = "partial"

    requested_workspace_id = _requested_workspace_id_from_action(selected_action_id, action_schema=action_schema)
    if requested_workspace_id is not None:
        active_workspace_id = requested_workspace_id
    elif coordination_vm.active_panel in {"circuit_library", "feedback_channel"}:
        active_workspace_id = "library"
    elif coordination_vm.active_panel in {"result_history", "execution", "trace_timeline", "artifact"} or shell_mode in {"runtime_monitoring", "run_review"}:
        active_workspace_id = "runtime_monitoring"
    elif shell_mode == "designer_review" or (beginner_mode and empty_workspace_mode):
        active_workspace_id = "node_configuration"
    else:
        active_workspace_id = "visual_editor"

    top_bar_vm = read_builder_top_bar_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        action_schema=action_schema,
        approval_flow=approval_flow,
    )
    command_palette_vm = read_command_palette_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        graph_view=graph_vm,
        action_schema=action_schema,
        coordination_state=coordination_vm,
        approval_flow=approval_flow,
    )

    beginner_onboarding = _beginner_onboarding_hint(
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        validation_vm=validation_vm,
        designer_vm=designer_vm,
        execution_vm=execution_vm,
        app_language=app_language,
    )
    beginner_surface_policy = _beginner_surface_policy(
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        active_workspace_id=active_workspace_id,
        validation_vm=validation_vm,
        execution_vm=execution_vm,
        app_language=app_language,
    )
    contextual_help = read_contextual_help_view(
        source_unwrapped,
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        validation_view=validation_vm,
        designer_view=designer_vm,
        execution_view=execution_vm,
        app_language=app_language,
    )
    privacy_transparency = read_privacy_transparency_view(
        source_unwrapped,
        designer_view=designer_vm,
        app_language=app_language,
    )
    mobile_first_run = read_mobile_first_run_view(
        source_unwrapped,
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        designer_view=designer_vm,
        execution_view=execution_vm,
        app_language=app_language,
    )
    first_success_preflight_vm = _first_success_preflight_view(first_success_preflight)
    workspace_chain_vm = _workspace_chain_review(
        storage_role=role,
        shell_mode=shell_mode,
        visual_editor_vm=visual_editor_vm,
        node_configuration_vm=node_configuration_vm,
        runtime_monitoring_vm=runtime_monitoring_vm,
        app_language=app_language,
    )
    product_readiness_vm = _product_readiness_review(
        source=source_unwrapped if source_unwrapped is not None else execution_record,
        execution_record=execution_record,
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        designer_vm=designer_vm,
        validation_vm=validation_vm,
        execution_vm=execution_vm,
        circuit_library_vm=circuit_library_vm,
        result_history_vm=result_history_vm,
        feedback_channel_vm=feedback_channel_vm,
        contextual_help=contextual_help,
        privacy_transparency=privacy_transparency,
        mobile_first_run=mobile_first_run,
        first_success_preflight=first_success_preflight_vm,
        app_language=app_language,
    )
    first_success_flow_vm = _first_success_flow_review(
        source=source_unwrapped if source_unwrapped is not None else execution_record,
        execution_record=execution_record,
        beginner_mode=beginner_mode,
        empty_workspace_mode=empty_workspace_mode,
        advanced_unlocked=advanced_unlocked,
        designer_vm=designer_vm,
        validation_vm=validation_vm,
        execution_vm=execution_vm,
        first_success_preflight=first_success_preflight_vm,
        product_readiness=product_readiness_vm,
        app_language=app_language,
    )

    return BuilderShellViewModel(
        shell_status=shell_status,
        shell_status_label=ui_text(f"shell.status.{shell_status}", app_language=app_language, fallback_text=shell_status.replace("_", " ")),
        storage_role=role,
        shell_mode=shell_mode,
        shell_mode_label=ui_text(f"shell.mode.{shell_mode}", app_language=app_language, fallback_text=shell_mode.replace("_", " ")),
        active_workspace_id=active_workspace_id,
        active_workspace_label=beginner_ui_text(f"workspace.{active_workspace_id}.name", beginner_text_key=(f"workspace.{active_workspace_id}.name.beginner" if active_workspace_id == "node_configuration" else None), sources=(source_unwrapped, execution_record), app_language=app_language, fallback_text=active_workspace_id.replace("_", " ")),
        top_bar=top_bar_vm,
        command_palette=command_palette_vm,
        coordination=coordination_vm,
        action_schema=action_schema,
        graph=graph_vm,
        inspector=inspector_vm,
        validation=validation_vm,
        storage=storage_vm,
        execution=execution_vm,
        trace_timeline=trace_vm,
        artifact=artifact_vm,
        diff=diff_vm,
        designer=designer_vm,
        visual_editor=visual_editor_vm,
        runtime_monitoring=runtime_monitoring_vm,
        node_configuration=node_configuration_vm,
        circuit_library=circuit_library_vm,
        result_history=result_history_vm,
        feedback_channel=feedback_channel_vm,
        workspace_chain=workspace_chain_vm,
        product_readiness=product_readiness_vm,
        first_success_preflight=first_success_preflight_vm,
        first_success_flow=first_success_flow_vm,
        layout=layout_vm,
        diagnostics=diagnostics,
        beginner_onboarding=beginner_onboarding,
        beginner_surface_policy=beginner_surface_policy,
        contextual_help=contextual_help,
        privacy_transparency=privacy_transparency,
        mobile_first_run=mobile_first_run,
        explanation=explanation,
    )


__all__ = [
    "BuilderShellLayoutView",
    "BuilderShellDiagnosticsView",
    "BeginnerOnboardingHintView",
    "BeginnerSurfacePolicyView",
    "WorkspaceChainStageView",
    "WorkspaceChainReviewView",
    "ProductSurfaceStageView",
    "FirstSuccessPreflightBlockerView",
    "FirstSuccessPreflightView",
    "FirstSuccessStepView",
    "FirstSuccessResultView",
    "FirstSuccessDesignerProposalView",
    "FirstSuccessFlowView",
    "ProductReadinessReviewView",
    "BuilderShellViewModel",
    "read_builder_shell_view_model",
]
