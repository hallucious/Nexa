from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.server.first_success_blockers import FirstSuccessBlocker, FirstSuccessPreflightSummary
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
from src.ui.builder_shell import read_builder_shell_view_model


def _working_save(*, nodes: list[dict] | None = None, metadata: dict | None = None) -> WorkingSaveModel:
    node_list = nodes if nodes is not None else [{"id": "n1", "kind": "provider", "label": "Summarize"}]
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="First Success Draft",
        ),
        circuit=CircuitModel(
            nodes=node_list,
            edges=[],
            entry=(str(node_list[0].get("id")) if node_list else None),
            outputs=([{"name": "result", "source": "node.n1.output.result"}] if node_list else []),
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=metadata or {"app_language": "en-US"}),
    )


def _blocked_validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[
            ValidationFinding(
                code="PROVIDER_MISSING",
                category="provider",
                severity="high",
                blocking=True,
                location="node:n1",
                message="Step 1 has no AI model selected.",
                hint="Choose an AI model.",
            )
        ],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )


def _clean_validation() -> ValidationReport:
    return ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed")


def _completed_execution() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-06T00:00:00Z",
            started_at="2026-04-06T00:00:00Z",
            finished_at="2026-04-06T00:00:05Z",
            status="completed",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="Readable result"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_first_success_flow_starts_empty_beginner_workspace_from_designer() -> None:
    vm = read_builder_shell_view_model(_working_save(nodes=[]))

    assert vm.first_success_flow.visible is True
    assert vm.first_success_flow.flow_state == "in_progress"
    assert vm.first_success_flow.current_step_id == "describe_goal"
    assert vm.first_success_flow.next_action_id == "open_designer"
    assert vm.first_success_flow.preferred_workspace_id == "node_configuration"
    assert vm.first_success_flow.preferred_panel_id == "designer"
    assert vm.active_workspace_id == "node_configuration"
    assert vm.coordination.active_panel == "designer"
    assert vm.beginner_surface_policy.primary_surface_id == "designer"


def test_first_success_flow_compresses_blocked_validation_into_review_step() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_blocked_validation(),
    )

    assert vm.validation is not None
    assert vm.validation.beginner_mode is True
    assert vm.validation.hide_raw_findings_by_default is True
    assert vm.validation.beginner_summary.status_signal == "Cannot run yet."
    assert vm.validation.beginner_summary.cause == "Step 1 has no AI model selected."

    assert vm.first_success_flow.flow_state == "blocked"
    assert vm.first_success_flow.current_step_id == "review_workflow"
    assert vm.first_success_flow.next_action_id == "open_node_configuration"
    assert vm.first_success_flow.preferred_panel_id == "validation"
    review_step = next(step for step in vm.first_success_flow.steps if step.step_id == "review_workflow")
    assert review_step.state == "blocked"
    assert review_step.summary == "Step 1 has no AI model selected."


def test_first_success_flow_uses_preflight_blocker_before_run() -> None:
    preflight = FirstSuccessPreflightSummary(
        ready=False,
        blockers=(
            FirstSuccessBlocker(
                family="file_extraction",
                reason_code="file_extraction.not_ready.failed",
                message="Document text extraction failed.",
                next_action="Upload a new document or retry extraction before running.",
                source_ref="fex-1",
            ),
        ),
    )

    vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_clean_validation(),
        session_keys={"gpt": "sk-test"},
        first_success_preflight=preflight,
    )

    assert vm.first_success_flow.flow_state == "blocked"
    assert vm.first_success_flow.current_step_id == "run_workflow"
    assert vm.first_success_flow.next_action_id == "open_file_input"
    assert vm.first_success_flow.preferred_panel_id == "designer"
    run_step = next(step for step in vm.first_success_flow.steps if step.step_id == "run_workflow")
    assert run_step.state == "blocked"
    assert run_step.summary == "Document text extraction failed."


def test_first_success_flow_marks_metadata_first_success_as_complete_and_unlocks_advanced_surfaces() -> None:
    vm = read_builder_shell_view_model(
        _working_save(metadata={"app_language": "en-US", "beginner_first_success_achieved": True}),
        execution_record=_completed_execution(),
    )

    assert vm.first_success_flow.visible is True
    assert vm.first_success_flow.flow_state == "complete"
    assert vm.first_success_flow.advanced_surfaces_unlocked is True
    assert vm.first_success_flow.unlock_condition == "already_unlocked"
    assert {step.state for step in vm.first_success_flow.steps} == {"complete"}
    assert vm.diagnostics.advanced_surfaces_unlocked is True
    assert vm.beginner_surface_policy.visible is False
