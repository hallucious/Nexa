from __future__ import annotations

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
from src.ui.beginner_milestones import apply_beginner_first_success_completion
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


def _action_ids(vm) -> set[str]:
    return {
        action.action_id
        for action in [
            *vm.action_schema.primary_actions,
            *vm.action_schema.secondary_actions,
            *vm.action_schema.contextual_actions,
        ]
        if action.enabled
    }


def test_first_success_result_reading_exposes_metadata_completion_action() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        execution_record=_completed_record(),
    )

    result = vm.first_success_flow.result_reading
    assert result.visible is True
    assert result.state == "ready_to_read"
    assert result.completion_action_id == "mark_first_result_read"
    assert result.completion_action_label == "Mark result as read"
    assert result.completion_metadata_patch == {
        "beginner_first_success_achieved": True,
        "advanced_surfaces_unlocked": True,
        "beginner_current_step": "read_result",
        "beginner_first_success_run_id": "run-001",
        "beginner_first_success_output_ref": "final",
        "beginner_first_success_artifact_ref": "artifact://final",
    }
    assert "mark_first_result_read" in _action_ids(vm)
    assert "open_result_history" not in _action_ids(vm)


def test_first_success_completion_metadata_unlocks_advanced_surfaces_and_return_actions() -> None:
    completed = apply_beginner_first_success_completion(
        _working_save(),
        run_id="run-001",
        output_ref="final",
        artifact_ref="artifact://final",
    )

    assert completed.ui.metadata["beginner_first_success_achieved"] is True
    assert completed.ui.metadata["advanced_surfaces_unlocked"] is True
    assert completed.ui.metadata["beginner_current_step"] == "read_result"

    vm = read_builder_shell_view_model(
        completed,
        execution_record=_completed_record(),
    )

    assert vm.first_success_flow.flow_state == "complete"
    assert vm.first_success_flow.result_reading.read_complete is True
    assert vm.first_success_flow.advanced_surfaces_unlocked is True
    assert "open_result_history" in _action_ids(vm)
    assert "mark_first_result_read" not in _action_ids(vm)
