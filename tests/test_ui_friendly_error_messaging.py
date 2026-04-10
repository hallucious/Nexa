from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.storage.models.execution_record_model import (
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionIssue,
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
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.validation_panel import read_validation_panel_view_model


def _working_save(*, last_run=None, errors=None) -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "draft"}], edges=[], entry="draft", outputs=[{"name": "out", "source": "draft"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run=last_run or {}, errors=errors or []),
        ui=UIModel(layout={}, metadata={}),
    )


def _record(*, termination_reason: str | None = None) -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="failed",
            title="Demo Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=5000, event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(
            warnings=[],
            errors=[ExecutionIssue(issue_code="RUNTIME_ERROR", category="runtime", severity="high", location="node:draft", message="run failed")],
            termination_reason=termination_reason,
        ),
        observability=ExecutionObservabilityModel(),
    )


def test_execution_panel_surfaces_friendly_api_key_missing_message() -> None:
    source = _working_save(errors=[{"issue_code": "API_KEY_MISSING", "message": "OPENAI_API_KEY missing"}])

    vm = read_execution_panel_view_model(source)

    assert vm.friendly_error.visible is True
    assert vm.friendly_error.error_code == "API_KEY_MISSING"
    assert vm.friendly_error.action_label == "Open setup"
    assert vm.friendly_error.action_target == "provider_setup"



def test_execution_panel_surfaces_friendly_quota_message_from_governance_summary() -> None:
    source = _working_save(last_run={"quota_status": "blocked", "quota_reason_code": "quota.run.count_limit_exceeded"})

    vm = read_execution_panel_view_model(source)

    assert vm.friendly_error.visible is True
    assert vm.friendly_error.error_code == "QUOTA_EXCEEDED"
    assert vm.friendly_error.action_label == "Review limit"



def test_execution_panel_surfaces_friendly_network_message_from_termination_reason() -> None:
    vm = read_execution_panel_view_model(_record(termination_reason="network connection failed"))

    assert vm.friendly_error.visible is True
    assert vm.friendly_error.error_code == "NETWORK_ERROR"
    assert vm.friendly_error.action_label == "Try again"



def test_validation_panel_surfaces_friendly_api_key_missing_message_from_validation_report() -> None:
    source = _working_save()
    report = ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="API_KEY_MISSING", category="runtime", severity="high", blocking=True, location="node:draft", message="OPENAI_API_KEY missing")],
        blocking_count=1,
        warning_count=0,
        result="failed",
    )

    vm = read_validation_panel_view_model(source, validation_report=report)

    assert vm.friendly_error.visible is True
    assert vm.friendly_error.error_code == "API_KEY_MISSING"
    assert vm.friendly_error.action_target == "provider_setup"



def test_validation_panel_surfaces_friendly_input_safety_message_from_governance_summary() -> None:
    source = _working_save(last_run={"safety_status": "blocked", "safety_reason_code": "safety.credential.exposed_secret_pattern"})

    vm = read_validation_panel_view_model(source)

    assert vm.friendly_error.visible is True
    assert vm.friendly_error.error_code == "INPUT_SAFETY_BLOCKED"
    assert vm.friendly_error.action_label == "Review input"
