from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_interaction_hub import read_builder_interaction_hub_view_model
from src.ui.interaction_lifecycle import read_interaction_lifecycle_view_model


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


def test_interaction_lifecycle_orders_builder_progression_from_drafting_to_execution() -> None:
    hub = read_builder_interaction_hub_view_model(_working_save(), validation_report=ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed"), execution_record=_run())
    vm = read_interaction_lifecycle_view_model(_working_save(), interaction_hub=hub)

    assert vm.current_stage_id in {"drafting", "review", "execution"}
    assert any(stage.stage_id == "execution" for stage in vm.stages)
    assert vm.lifecycle_status in {"ready", "attention"}


def test_interaction_lifecycle_marks_execution_record_as_history_terminal() -> None:
    vm = read_interaction_lifecycle_view_model(_run())

    assert vm.source_role == "execution_record"
    assert vm.terminal is True
    assert vm.lifecycle_status == "terminal"
    assert vm.current_stage_id == "history"
