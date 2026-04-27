from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_interaction_hub import read_builder_interaction_hub_view_model
from src.ui.command_dispatch_contract import read_command_dispatch_contract_view_model


from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.action_schema import read_builder_action_schema
from src.ui.command_routing import read_builder_command_routing_view_model
from src.ui.intent_emission import read_intent_emission_view_model
def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
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


def test_command_dispatch_contract_exposes_required_fields_and_boundary_targets() -> None:
    hub = read_builder_interaction_hub_view_model(_working_save(), validation_report=ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed"), execution_record=_run())
    vm = read_command_dispatch_contract_view_model(_working_save(), interaction_hub=hub)
    run_current = next(item for item in vm.contracts if item.action_id == "run_current")

    assert vm.dispatch_status in {"ready", "attention"}
    assert vm.enabled_dispatch_count >= 1
    assert run_current.boundary_target == "execution_runner"
    assert any(field.field_name == "target_ref" for field in run_current.required_fields)


def test_command_dispatch_contract_marks_execution_record_terminal_when_dispatch_is_available() -> None:
    vm = read_command_dispatch_contract_view_model(_run())

    assert vm.source_role == "execution_record"
    assert vm.enabled_dispatch_count >= 1
    assert vm.dispatch_status == "terminal"


def test_command_dispatch_contract_exposes_required_fields_for_beginner_productization_actions() -> None:
    working = _working_save()
    working.ui.metadata["beginner_first_success_achieved"] = True

    hub = read_builder_interaction_hub_view_model(
        working,
        validation_report=ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed"),
        execution_record=_run(),
    )
    vm = read_command_dispatch_contract_view_model(working, interaction_hub=hub)
    result_history = next(item for item in vm.contracts if item.action_id == "open_result_history")
    file_input = next(item for item in vm.contracts if item.action_id == "open_file_input")

    assert result_history.boundary_target == "ui_boundary"
    assert any(field.field_name == "working_save_id" for field in file_input.required_fields)
    assert any(field.field_name == "run_id" for field in result_history.required_fields)


def test_dispatch_contract_includes_core_workspace_navigation_fields() -> None:
    working = _working_save()
    working.ui.metadata["beginner_first_success_achieved"] = True
    interaction_hub = read_builder_interaction_hub_view_model(working, execution_record=_run())
    intent_emission = read_intent_emission_view_model(working, interaction_hub=interaction_hub)

    vm = read_command_dispatch_contract_view_model(working, interaction_hub=interaction_hub, intent_emission=intent_emission)
    contracts = {item.action_id: item for item in vm.contracts}
    assert [field.field_name for field in contracts["open_visual_editor"].required_fields] == ["workspace_id", "panel_id"]
    assert [field.field_name for field in contracts["open_node_configuration"].required_fields] == ["workspace_id", "panel_id"]
    assert [field.field_name for field in contracts["open_runtime_monitoring"].required_fields] == ["workspace_id", "panel_id"]


def test_command_routing_blocks_beginner_locked_deep_surface_actions_before_first_success() -> None:
    working = _working_save()
    execution = read_execution_panel_view_model(working, execution_record=_run())
    action_schema = read_builder_action_schema(working, execution_view=execution)

    vm = read_builder_command_routing_view_model(working, action_schema=action_schema)
    routes = {route.action_id: route for route in vm.routes}

    assert routes["replay_latest"].enabled is False
    assert routes["open_diff"].enabled is False
    assert routes["replay_latest"].reason_disabled is not None
    assert routes["open_diff"].reason_disabled is not None


def test_command_dispatch_blocks_beginner_locked_deep_surface_actions_before_first_success() -> None:
    working = _working_save()
    execution = read_execution_panel_view_model(working, execution_record=_run())
    action_schema = read_builder_action_schema(working, execution_view=execution)
    routing = read_builder_command_routing_view_model(working, action_schema=action_schema)

    vm = read_command_dispatch_contract_view_model(working, command_routing=routing)
    contracts = {item.action_id: item for item in vm.contracts}

    assert contracts["replay_latest"].dispatch_allowed is False
    assert contracts["open_diff"].dispatch_allowed is False
