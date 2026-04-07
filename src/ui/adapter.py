from __future__ import annotations

from dataclasses import dataclass

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel, read_trace_timeline_view_model
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.inspector_panel import SelectedObjectViewModel, read_selected_object_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model
from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
from src.ui.builder_shell import BuilderShellViewModel, read_builder_shell_view_model
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.visual_editor_workspace import VisualEditorWorkspaceViewModel, read_visual_editor_workspace_view_model
from src.ui.node_configuration_workspace import NodeConfigurationWorkspaceViewModel, read_node_configuration_workspace_view_model
from src.ui.runtime_monitoring_workspace import RuntimeMonitoringWorkspaceViewModel, read_runtime_monitoring_workspace_view_model
from src.ui.proposal_commit_workflow import ProposalCommitWorkflowViewModel, read_proposal_commit_workflow_view_model
from src.ui.execution_launch_workflow import ExecutionLaunchWorkflowViewModel, read_execution_launch_workflow_view_model
from src.ui.builder_workflow_hub import BuilderWorkflowHubViewModel, read_builder_workflow_hub_view_model
from src.ui.command_routing import BuilderCommandRoutingViewModel, read_builder_command_routing_view_model
from src.ui.interaction_transitions import BuilderInteractionTransitionViewModel, read_builder_interaction_transition_view_model
from src.ui.builder_interaction_hub import BuilderInteractionHubViewModel, read_builder_interaction_hub_view_model
from src.ui.intent_emission import IntentEmissionViewModel, read_intent_emission_view_model
from src.ui.command_dispatch_contract import CommandDispatchContractViewModel, read_command_dispatch_contract_view_model
from src.ui.interaction_lifecycle import InteractionLifecycleViewModel, read_interaction_lifecycle_view_model
from src.ui.builder_dispatch_hub import BuilderDispatchHubViewModel, read_builder_dispatch_hub_view_model
from src.ui.command_execution_adapter import CommandExecutionAdapterViewModel, read_command_execution_adapter_view_model
from src.ui.interaction_state_changes import InteractionStateChangeViewModel, read_interaction_state_change_view_model
from src.ui.builder_execution_adapter_hub import BuilderExecutionAdapterHubViewModel, read_builder_execution_adapter_hub_view_model
from src.ui.end_user_command_flows import EndUserCommandFlowViewModel, read_end_user_command_flow_view_model
from src.ui.interaction_lifecycle_closure import InteractionLifecycleClosureViewModel, read_interaction_lifecycle_closure_view_model
from src.ui.builder_end_user_flow_hub import BuilderEndUserFlowHubViewModel, read_builder_end_user_flow_hub_view_model


@dataclass(frozen=True)
class NexaUIViewAdapter:
    latest_working_save: WorkingSaveModel | None = None
    latest_commit_snapshot: CommitSnapshotModel | None = None
    latest_execution_record: ExecutionRecordModel | None = None

    def read_graph_view_model(
        self,
        source: WorkingSaveModel | CommitSnapshotModel | LoadedNexArtifact,
        *,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
    ) -> GraphWorkspaceViewModel:
        return read_graph_view_model(
            source,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
        )

    def read_storage_view_model(
        self,
        active_source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
        *,
        explanation: str | None = None,
    ) -> StoragePanelViewModel:
        return read_storage_view_model(
            active_source,
            latest_working_save=self.latest_working_save,
            latest_commit_snapshot=self.latest_commit_snapshot,
            latest_execution_record=self.latest_execution_record,
            explanation=explanation,
        )


    def read_execution_panel_view_model(
        self,
        source,
        *,
        execution_record: ExecutionRecordModel | None = None,
        live_events=None,
        explanation: str | None = None,
    ) -> ExecutionPanelViewModel:
        return read_execution_panel_view_model(
            source,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            live_events=live_events,
            explanation=explanation,
        )

    def read_trace_timeline_view_model(
        self,
        source,
        *,
        execution_record: ExecutionRecordModel | None = None,
        live_events=None,
        explanation: str | None = None,
    ) -> TraceTimelineViewerViewModel:
        return read_trace_timeline_view_model(
            source,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            live_events=live_events,
            explanation=explanation,
        )


    def read_inspector_panel_view_model(
        self,
        source,
        *,
        selected_ref: str | None = None,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        explanation: str | None = None,
    ) -> SelectedObjectViewModel:
        return read_selected_object_view_model(
            source,
            selected_ref=selected_ref,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            explanation=explanation,
        )

    def read_validation_panel_view_model(
        self,
        source,
        *,
        validation_report: ValidationReport | None = None,
        precheck=None,
        execution_record: ExecutionRecordModel | None = None,
        explanation: str | None = None,
    ) -> ValidationPanelViewModel:
        return read_validation_panel_view_model(
            source,
            validation_report=validation_report,
            precheck=precheck,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            explanation=explanation,
        )

    def read_designer_panel_view_model(
        self,
        source,
        *,
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> DesignerPanelViewModel:
        return read_designer_panel_view_model(
            source,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            explanation=explanation,
        )

    def read_artifact_viewer_view_model(
        self,
        source,
        *,
        execution_record: ExecutionRecordModel | None = None,
        selected_artifact_id: str | None = None,
        explanation: str | None = None,
    ) -> ArtifactViewerViewModel:
        return read_artifact_viewer_view_model(
            source,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            selected_artifact_id=selected_artifact_id,
            explanation=explanation,
        )

    def read_diff_view_model(
        self,
        *,
        diff_mode: str,
        source,
        target,
        explanation: str | None = None,
    ) -> DiffViewerViewModel:
        return read_diff_view_model(diff_mode=diff_mode, source=source, target=target, explanation=explanation)

    def read_builder_action_schema_view(
        self,
        source,
        *,
        storage_view: StoragePanelViewModel | None = None,
        validation_view: ValidationPanelViewModel | None = None,
        execution_view: ExecutionPanelViewModel | None = None,
        designer_view: DesignerPanelViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderActionSchemaView:
        return read_builder_action_schema(
            source,
            storage_view=storage_view,
            validation_view=validation_view,
            execution_view=execution_view,
            designer_view=designer_view,
            explanation=explanation,
        )

    def read_panel_coordination_state_view(
        self,
        source,
        *,
        graph_view: GraphWorkspaceViewModel | None = None,
        storage_view: StoragePanelViewModel | None = None,
        diff_view: DiffViewerViewModel | None = None,
        execution_view: ExecutionPanelViewModel | None = None,
        validation_view: ValidationPanelViewModel | None = None,
        designer_view: DesignerPanelViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderPanelCoordinationStateView:
        return read_panel_coordination_state(
            source,
            graph_view=graph_view,
            storage_view=storage_view,
            diff_view=diff_view,
            execution_view=execution_view,
            validation_view=validation_view,
            designer_view=designer_view,
            explanation=explanation,
        )

    def read_builder_shell_view_model(
        self,
        source,
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
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> BuilderShellViewModel:
        return read_builder_shell_view_model(
            source,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
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
            explanation=explanation,
        )

    def read_visual_editor_workspace_view_model(
        self,
        source,
        *,
        validation_report: ValidationReport | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        diff_mode: str | None = None,
        diff_source=None,
        diff_target=None,
        explanation: str | None = None,
    ) -> VisualEditorWorkspaceViewModel:
        return read_visual_editor_workspace_view_model(
            source,
            validation_report=validation_report,
            preview_overlay=preview_overlay,
            diff_mode=diff_mode,
            diff_source=diff_source,
            diff_target=diff_target,
            explanation=explanation,
        )

    def read_node_configuration_workspace_view_model(
        self,
        source,
        *,
        selected_ref: str | None = None,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> NodeConfigurationWorkspaceViewModel:
        return read_node_configuration_workspace_view_model(
            source,
            selected_ref=selected_ref,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            explanation=explanation,
        )

    def read_runtime_monitoring_workspace_view_model(
        self,
        source,
        *,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        live_events=None,
        selected_artifact_id: str | None = None,
        explanation: str | None = None,
    ) -> RuntimeMonitoringWorkspaceViewModel:
        return read_runtime_monitoring_workspace_view_model(
            source,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            live_events=live_events,
            selected_artifact_id=selected_artifact_id,
            explanation=explanation,
        )

    def read_proposal_commit_workflow_view_model(
        self,
        source,
        *,
        selected_ref: str | None = None,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> ProposalCommitWorkflowViewModel:
        return read_proposal_commit_workflow_view_model(
            source,
            selected_ref=selected_ref,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            explanation=explanation,
        )

    def read_execution_launch_workflow_view_model(
        self,
        source,
        *,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        live_events=None,
        selected_artifact_id: str | None = None,
        explanation: str | None = None,
    ) -> ExecutionLaunchWorkflowViewModel:
        return read_execution_launch_workflow_view_model(
            source,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            live_events=live_events,
            selected_artifact_id=selected_artifact_id,
            explanation=explanation,
        )

    def read_builder_workflow_hub_view_model(
        self,
        source,
        *,
        selected_ref: str | None = None,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        live_events=None,
        selected_artifact_id: str | None = None,
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> BuilderWorkflowHubViewModel:
        return read_builder_workflow_hub_view_model(
            source,
            selected_ref=selected_ref,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            live_events=live_events,
            selected_artifact_id=selected_artifact_id,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            explanation=explanation,
        )


    def read_builder_command_routing_view_model(
        self,
        source,
        *,
        action_schema: BuilderActionSchemaView | None = None,
        workflow_hub: BuilderWorkflowHubViewModel | None = None,
        coordination_state: BuilderPanelCoordinationStateView | None = None,
        explanation: str | None = None,
    ) -> BuilderCommandRoutingViewModel:
        return read_builder_command_routing_view_model(
            source,
            action_schema=action_schema,
            workflow_hub=workflow_hub,
            coordination_state=coordination_state,
            explanation=explanation,
        )

    def read_builder_interaction_transition_view_model(
        self,
        source,
        *,
        command_routing: BuilderCommandRoutingViewModel,
        workflow_hub: BuilderWorkflowHubViewModel | None = None,
        coordination_state: BuilderPanelCoordinationStateView | None = None,
        selected_action_id: str | None = None,
        explanation: str | None = None,
    ) -> BuilderInteractionTransitionViewModel:
        return read_builder_interaction_transition_view_model(
            source,
            command_routing=command_routing,
            workflow_hub=workflow_hub,
            coordination_state=coordination_state,
            selected_action_id=selected_action_id,
            explanation=explanation,
        )

    def read_builder_interaction_hub_view_model(
        self,
        source,
        *,
        selected_ref: str | None = None,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        live_events=None,
        selected_artifact_id: str | None = None,
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        selected_action_id: str | None = None,
        explanation: str | None = None,
    ) -> BuilderInteractionHubViewModel:
        return read_builder_interaction_hub_view_model(
            source,
            selected_ref=selected_ref,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            live_events=live_events,
            selected_artifact_id=selected_artifact_id,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            selected_action_id=selected_action_id,
            explanation=explanation,
        )


    def read_intent_emission_view_model(
        self,
        source,
        *,
        interaction_hub: BuilderInteractionHubViewModel | None = None,
        explanation: str | None = None,
    ) -> IntentEmissionViewModel:
        return read_intent_emission_view_model(
            source,
            interaction_hub=interaction_hub,
            explanation=explanation,
        )

    def read_command_dispatch_contract_view_model(
        self,
        source,
        *,
        interaction_hub: BuilderInteractionHubViewModel | None = None,
        command_routing: BuilderCommandRoutingViewModel | None = None,
        intent_emission: IntentEmissionViewModel | None = None,
        explanation: str | None = None,
    ) -> CommandDispatchContractViewModel:
        return read_command_dispatch_contract_view_model(
            source,
            interaction_hub=interaction_hub,
            command_routing=command_routing,
            intent_emission=intent_emission,
            explanation=explanation,
        )

    def read_interaction_lifecycle_view_model(
        self,
        source,
        *,
        interaction_hub: BuilderInteractionHubViewModel | None = None,
        dispatch_contract: CommandDispatchContractViewModel | None = None,
        explanation: str | None = None,
    ) -> InteractionLifecycleViewModel:
        return read_interaction_lifecycle_view_model(
            source,
            interaction_hub=interaction_hub,
            dispatch_contract=dispatch_contract,
            explanation=explanation,
        )


    def read_builder_dispatch_hub_view_model(
        self,
        source,
        *,
        interaction_hub: BuilderInteractionHubViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderDispatchHubViewModel:
        return read_builder_dispatch_hub_view_model(
            source,
            interaction_hub=interaction_hub,
            explanation=explanation,
        )



    def read_command_execution_adapter_view_model(
        self,
        source,
        *,
        dispatch_hub: BuilderDispatchHubViewModel | None = None,
        explanation: str | None = None,
    ) -> CommandExecutionAdapterViewModel:
        return read_command_execution_adapter_view_model(
            source,
            dispatch_hub=dispatch_hub,
            explanation=explanation,
        )

    def read_interaction_state_change_view_model(
        self,
        source,
        *,
        dispatch_hub: BuilderDispatchHubViewModel | None = None,
        execution_adapters: CommandExecutionAdapterViewModel | None = None,
        explanation: str | None = None,
    ) -> InteractionStateChangeViewModel:
        return read_interaction_state_change_view_model(
            source,
            dispatch_hub=dispatch_hub,
            execution_adapters=execution_adapters,
            explanation=explanation,
        )

    def read_builder_execution_adapter_hub_view_model(
        self,
        source,
        *,
        dispatch_hub: BuilderDispatchHubViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderExecutionAdapterHubViewModel:
        return read_builder_execution_adapter_hub_view_model(
            source,
            dispatch_hub=dispatch_hub,
            explanation=explanation,
        )

    def read_end_user_command_flow_view_model(
        self,
        source,
        *,
        execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None,
        explanation: str | None = None,
    ) -> EndUserCommandFlowViewModel:
        return read_end_user_command_flow_view_model(
            source,
            execution_adapter_hub=execution_adapter_hub,
            explanation=explanation,
        )

    def read_interaction_lifecycle_closure_view_model(
        self,
        source,
        *,
        execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None,
        end_user_flows: EndUserCommandFlowViewModel | None = None,
        explanation: str | None = None,
    ) -> InteractionLifecycleClosureViewModel:
        return read_interaction_lifecycle_closure_view_model(
            source,
            execution_adapter_hub=execution_adapter_hub,
            end_user_flows=end_user_flows,
            explanation=explanation,
        )

    def read_builder_end_user_flow_hub_view_model(
        self,
        source,
        *,
        execution_adapter_hub: BuilderExecutionAdapterHubViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderEndUserFlowHubViewModel:
        return read_builder_end_user_flow_hub_view_model(
            source,
            execution_adapter_hub=execution_adapter_hub,
            explanation=explanation,
        )


__all__ = ["NexaUIViewAdapter"]
