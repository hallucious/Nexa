from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.inspector_panel import SelectedObjectViewModel, read_selected_object_view_model
from src.ui.i18n import beginner_ui_text, ui_language_from_sources, ui_text
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
    layout: BuilderShellLayoutView = field(default_factory=BuilderShellLayoutView)
    diagnostics: BuilderShellDiagnosticsView = field(default_factory=BuilderShellDiagnosticsView)
    beginner_onboarding: BeginnerOnboardingHintView = field(default_factory=BeginnerOnboardingHintView)
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


def _is_empty_working_save(source: WorkingSaveModel | None) -> bool:
    if not isinstance(source, WorkingSaveModel):
        return False
    return not source.circuit.nodes and not source.circuit.edges


def _beginner_first_success_achieved(metadata: dict[str, Any], *, execution_vm: ExecutionPanelViewModel | None = None) -> bool:
    if bool(metadata.get("beginner_first_success_achieved")):
        return True
    if execution_vm is not None and execution_vm.execution_status == "completed" and execution_vm.run_identity.run_id is not None:
        return True
    return False


def _advanced_surfaces_unlocked(metadata: dict[str, Any], *, execution_vm: ExecutionPanelViewModel | None = None) -> bool:
    if bool(metadata.get("advanced_mode_requested")):
        return True
    if str(metadata.get("user_mode") or "").lower() == "advanced":
        return True
    return _beginner_first_success_achieved(metadata, execution_vm=execution_vm)


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
    )
    action_schema = read_builder_action_schema(
        source_unwrapped,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        designer_view=designer_vm,
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
    advanced_unlocked = _advanced_surfaces_unlocked(metadata, execution_vm=execution_vm)
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

    if coordination_vm.active_panel in {"execution", "trace_timeline", "artifact"} or shell_mode in {"runtime_monitoring", "run_review"}:
        active_workspace_id = "runtime_monitoring"
    elif shell_mode == "designer_review":
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
        layout=layout_vm,
        diagnostics=diagnostics,
        beginner_onboarding=beginner_onboarding,
        contextual_help=contextual_help,
        privacy_transparency=privacy_transparency,
        mobile_first_run=mobile_first_run,
        explanation=explanation,
    )


__all__ = [
    "BuilderShellLayoutView",
    "BuilderShellDiagnosticsView",
    "BeginnerOnboardingHintView",
    "BuilderShellViewModel",
    "read_builder_shell_view_model",
]
