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
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
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
    can_edit_configuration: bool = False
    can_submit_designer_request: bool = False
    can_commit_configuration: bool = False
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
    return None


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
    can_commit_configuration = any(action.action_id == "commit_snapshot" and action.enabled for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions])
    workspace_explanation = explanation or _workspace_explanation(
        workspace_status=workspace_status,
        app_language=app_language,
        validation_vm=validation_vm,
        designer_vm=designer_vm,
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
        can_edit_configuration=storage_role == "working_save" and selection_summary.object_type not in {"none", "unknown"},
        can_submit_designer_request=can_submit_designer_request,
        can_commit_configuration=can_commit_configuration,
        explanation=workspace_explanation,
    )


__all__ = [
    "ConfigurationSelectionSummaryView",
    "ConfigurationReviewStateView",
    "NodeConfigurationWorkspaceViewModel",
    "read_node_configuration_workspace_view_model",
]
