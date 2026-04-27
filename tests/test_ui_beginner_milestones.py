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
from src.ui.beginner_milestones import (
    beginner_advanced_surfaces_unlocked,
    beginner_surface_active,
    explicit_beginner_first_success_achieved,
    return_use_ready,
)


def _working_save(*, metadata: dict | None = None, last_run: dict | None = None) -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run=dict(last_run or {}), errors=[]),
        ui=UIModel(layout={}, metadata=dict(metadata or {})),
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-27T00:00:00Z", started_at="2026-04-27T00:00:00Z", finished_at="2026-04-27T00:00:05Z", status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_beginner_milestone_does_not_infer_first_success_from_completed_last_run() -> None:
    source = _working_save(last_run={"run_id": "run-local", "status": "completed"})

    assert beginner_surface_active(source) is True
    assert explicit_beginner_first_success_achieved(source) is False
    assert beginner_advanced_surfaces_unlocked(source) is False
    assert return_use_ready(source) is False


def test_beginner_milestone_unlocks_only_from_explicit_first_success_metadata() -> None:
    source = _working_save(metadata={"beginner_first_success_achieved": True}, last_run={"run_id": "run-local", "status": "completed"})

    assert beginner_surface_active(source) is True
    assert explicit_beginner_first_success_achieved(source) is True
    assert beginner_advanced_surfaces_unlocked(source) is True
    assert return_use_ready(source) is True


def test_beginner_milestone_treats_advanced_request_as_surface_unlock_not_first_success() -> None:
    source = _working_save(metadata={"advanced_mode_requested": True})

    assert beginner_surface_active(source) is False
    assert explicit_beginner_first_success_achieved(source) is False
    assert beginner_advanced_surfaces_unlocked(source) is True


def test_beginner_milestone_keeps_execution_record_runtime_truth_separate() -> None:
    record = _run("completed")

    assert beginner_surface_active(record) is False
    assert explicit_beginner_first_success_achieved(record) is False
    assert beginner_advanced_surfaces_unlocked(record) is True
    assert return_use_ready(record) is True
