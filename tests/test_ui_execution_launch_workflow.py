from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.execution_launch_workflow import read_execution_launch_workflow_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation_report(result: str = "passed") -> ValidationReport:
    if result == "failed":
        return ValidationReport(
            role="working_save",
            findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="blocked")],
            blocking_count=1,
            warning_count=0,
            result="failed",
        )
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n1", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def test_execution_launch_workflow_enters_live_monitoring_for_running_run() -> None:
    vm = read_execution_launch_workflow_view_model(_working_save(), validation_report=_validation_report(), execution_record=_run("running"))
    assert vm.workflow_status == "live_monitoring"
    assert vm.can_cancel is True
    assert vm.summary.launch_mode == "live_run"


def test_execution_launch_workflow_is_launch_ready_when_run_is_allowed() -> None:
    vm = read_execution_launch_workflow_view_model(_working_save(), validation_report=_validation_report(), execution_record=_run("completed"))
    assert vm.workflow_status in {"launch_ready", "replay_ready"}
    assert vm.can_launch is True or vm.can_replay is True


def test_execution_launch_workflow_localizes_next_step_for_korean_app_language() -> None:
    working = _working_save()
    working.ui.metadata["app_language"] = "ko-KR"

    vm = read_execution_launch_workflow_view_model(working, validation_report=_validation_report(), execution_record=_run("completed"))

    assert vm.summary.next_step_label in {"최신 실행 재실행 또는 검토", "현재 구조 실행"}
