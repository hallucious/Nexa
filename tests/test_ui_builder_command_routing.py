from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.action_schema import read_builder_action_schema
from src.ui.builder_workflow_hub import read_builder_workflow_hub_view_model
from src.ui.command_routing import read_builder_command_routing_view_model
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.panel_coordination import read_panel_coordination_state
from src.ui.storage_panel import read_storage_view_model
from src.ui.validation_panel import read_validation_panel_view_model
from src.contracts.execution_event_contract import ExecutionEvent


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _run() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation(result: str = "passed") -> ValidationReport:
    if result == "failed":
        return ValidationReport(role="working_save", findings=[], blocking_count=1, warning_count=0, result="failed")
    return ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed")


def test_builder_command_routing_projects_workspace_and_panel_targets() -> None:
    storage = read_storage_view_model(_working_save(), latest_commit_snapshot=_commit(), latest_execution_record=_run())
    validation = read_validation_panel_view_model(_working_save(), validation_report=_validation())
    execution = read_execution_panel_view_model(_working_save(), execution_record=_run())
    action_schema = read_builder_action_schema(_working_save(), storage_view=storage, validation_view=validation, execution_view=execution)
    coordination = read_panel_coordination_state(_working_save(), storage_view=storage, execution_view=execution, validation_view=validation)
    workflow_hub = read_builder_workflow_hub_view_model(_working_save(), validation_report=_validation(), execution_record=_run())

    routing = read_builder_command_routing_view_model(
        _working_save(),
        action_schema=action_schema,
        workflow_hub=workflow_hub,
        coordination_state=coordination,
    )

    run_route = next(route for route in routing.routes if route.action_id == "run_current")
    diff_route = next(route for route in routing.routes if route.action_id == "open_diff")
    commit_route = next(route for route in routing.routes if route.action_id == "commit_snapshot")

    assert routing.source_role == "working_save"
    assert run_route.preferred_workspace_id == "runtime_monitoring"
    assert run_route.preferred_panel_id == "execution"
    assert diff_route.preferred_workspace_id == "visual_editor"
    assert diff_route.preferred_panel_id == "diff"
    assert commit_route.engine_boundary == "commit_gateway"


def test_builder_command_routing_marks_disabled_routes_when_validation_blocks_run() -> None:
    live_events = [ExecutionEvent("execution_started", "run-001", None, 0, {})]
    validation = read_validation_panel_view_model(_working_save(), validation_report=_validation("failed"))
    execution = read_execution_panel_view_model(_working_save(), live_events=live_events)
    action_schema = read_builder_action_schema(_working_save(), validation_view=validation, execution_view=execution)

    routing = read_builder_command_routing_view_model(_working_save(), action_schema=action_schema)
    run_route = next(route for route in routing.routes if route.action_id == "run_current")
    cancel_route = next(route for route in routing.routes if route.action_id == "cancel_run")

    assert routing.disabled_route_count >= 1
    assert run_route.enabled is False
    assert cancel_route.enabled is True


from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView


def test_builder_command_routing_marks_blocked_when_all_routes_disabled() -> None:
    action_schema = BuilderActionSchemaView(
        source_role="working_save",
        primary_actions=[BuilderActionView("run_current", "Run", "execution", False, reason_disabled="blocked")],
        secondary_actions=[BuilderActionView("open_diff", "Diff", "comparison", False, reason_disabled="blocked")],
    )

    routing = read_builder_command_routing_view_model(_working_save(), action_schema=action_schema)

    assert routing.enabled_route_count == 0
    assert routing.disabled_route_count == 2
    assert routing.routing_status == "blocked"


def test_builder_command_routing_projects_productization_actions_into_explicit_workspace_targets() -> None:
    action_schema = BuilderActionSchemaView(
        source_role="working_save",
        contextual_actions=[
            BuilderActionView("open_provider_setup", "Connect AI model", "provider_setup", True),
            BuilderActionView("create_circuit_from_template", "Choose starter workflow", "template_gallery", True),
            BuilderActionView("open_file_input", "Use a file", "external_input", True),
            BuilderActionView("watch_run_progress", "Watch progress", "execution_monitoring", True),
            BuilderActionView("open_circuit_library", "Open workflow library", "return_use", True),
            BuilderActionView("open_result_history", "Open recent results", "return_use", True),
            BuilderActionView("open_feedback_channel", "Send feedback", "return_use", True),
        ],
    )

    routing = read_builder_command_routing_view_model(_working_save(), action_schema=action_schema)
    routes = {route.action_id: route for route in routing.routes}

    assert routes["open_provider_setup"].preferred_workspace_id == "node_configuration"
    assert routes["create_circuit_from_template"].preferred_panel_id == "designer"
    assert routes["open_file_input"].preferred_panel_id == "designer"
    assert routes["watch_run_progress"].preferred_workspace_id == "runtime_monitoring"
    assert routes["open_circuit_library"].preferred_workspace_id == "library"
    assert routes["open_result_history"].preferred_panel_id == "result_history"
    assert routes["open_feedback_channel"].preferred_panel_id == "feedback_channel"
