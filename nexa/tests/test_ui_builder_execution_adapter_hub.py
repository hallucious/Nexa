from __future__ import annotations

from src.storage.models.execution_record_model import (
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultsModel,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from dataclasses import replace
from src.ui.builder_execution_adapter_hub import read_builder_execution_adapter_hub_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
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


def test_builder_execution_adapter_hub_integrates_dispatch_adapters_and_state_changes() -> None:
    vm = read_builder_execution_adapter_hub_view_model(_working_save())

    assert vm.dispatch_hub is not None
    assert vm.execution_adapters is not None
    assert vm.state_changes is not None
    assert vm.executable_action_count >= 1
    assert vm.hub_status_label == "주의 필요"


def test_builder_execution_adapter_hub_prioritizes_terminal_status_for_execution_record() -> None:
    vm = read_builder_execution_adapter_hub_view_model(_run())

    assert vm.source_role == "execution_record"
    assert vm.dispatch_hub is not None
    assert vm.dispatch_hub.lifecycle is not None
    assert vm.dispatch_hub.lifecycle.terminal is True
    assert vm.hub_status == "terminal"


def test_builder_execution_adapter_hub_propagates_blocked_from_dispatch_hub() -> None:
    vm = read_builder_execution_adapter_hub_view_model(_working_save())
    assert vm.dispatch_hub is not None
    blocked_dispatch = replace(vm.dispatch_hub, hub_status="blocked")
    blocked_vm = read_builder_execution_adapter_hub_view_model(_working_save(), dispatch_hub=blocked_dispatch)
    assert blocked_vm.hub_status == "blocked"
