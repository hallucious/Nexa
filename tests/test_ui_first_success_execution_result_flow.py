from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.storage.models.execution_record_model import (
    ArtifactRecordCard,
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultCard,
    NodeResultsModel,
    OutputResultCard,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model


def _working_save(*, metadata: dict | None = None) -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="First Success Draft",
        ),
        circuit=CircuitModel(
            nodes=[{"id": "draft", "kind": "provider", "label": "Draft"}],
            edges=[],
            entry="draft",
            outputs=[{"name": "result", "source": "node.draft.output.result"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=metadata or {"app_language": "en-US"}),
    )


def _completed_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="completed",
            title="Demo Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=1, node_order=["draft"]),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="draft", status="success", output_summary="draft ready")]),
        outputs=ExecutionOutputModel(
            final_outputs=[
                OutputResultCard(
                    output_ref="final",
                    source_node="draft",
                    value_summary="Readable result",
                    value_type="text",
                    value_payload="Readable result body",
                )
            ],
            output_summary="Readable result",
        ),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[
                ArtifactRecordCard(
                    artifact_id="artifact-001",
                    artifact_type="final_output",
                    producer_node="draft",
                    ref="artifact://final",
                )
            ]
        ),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _blocked_validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[
            ValidationFinding(
                code="MISSING_MODEL",
                category="provider",
                severity="high",
                blocking=True,
                location="node:draft",
                message="Step 1 has no AI model selected.",
                hint="Choose an AI model.",
            )
        ],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )


def test_first_success_flow_exposes_readable_execution_result_without_unlocking_until_marked_read() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        execution_record=_completed_record(),
    )

    assert vm.execution is not None
    assert vm.execution.result_reading.visible is True
    assert vm.first_success_flow.current_step_id == "read_result"
    assert vm.first_success_flow.result_reading.visible is True
    assert vm.first_success_flow.result_reading.state == "ready_to_read"
    assert vm.first_success_flow.result_reading.summary == "Readable result"
    assert vm.first_success_flow.result_reading.primary_text == "Readable result body"
    assert vm.first_success_flow.result_reading.output_ref == "final"
    assert vm.first_success_flow.result_reading.artifact_ref == "artifact://final"
    assert vm.first_success_flow.result_reading.next_action_id == "open_runtime_monitoring"
    assert vm.first_success_flow.result_reading.read_complete is False
    assert vm.first_success_flow.advanced_surfaces_unlocked is False


def test_first_success_flow_marks_result_reading_complete_after_first_success_metadata() -> None:
    vm = read_builder_shell_view_model(
        _working_save(metadata={"app_language": "en-US", "beginner_first_success_achieved": True}),
        execution_record=_completed_record(),
    )

    assert vm.first_success_flow.flow_state == "complete"
    assert vm.first_success_flow.result_reading.visible is True
    assert vm.first_success_flow.result_reading.state == "complete"
    assert vm.first_success_flow.result_reading.read_complete is True
    assert vm.first_success_flow.result_reading.next_action_id == "open_result_history"
    assert vm.first_success_flow.advanced_surfaces_unlocked is True


def test_product_readiness_uses_compressed_validation_next_action() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_blocked_validation(),
    )

    run_stage = next(stage for stage in vm.product_readiness.stages if stage.stage_id == "first_success_run")
    assert run_stage.stage_state == "fix_before_run"
    assert run_stage.summary.startswith("Step 1 has no AI model selected.")
    assert "Review how your data is routed before the first run." in run_stage.summary
    assert run_stage.recommended_action_id == "open_node_configuration"
    assert run_stage.recommended_action_label == "Fix this step"
