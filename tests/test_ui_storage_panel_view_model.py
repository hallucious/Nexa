from __future__ import annotations

from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
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
    NodeResultsModel,
    OutputResultCard,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import DesignerDraftModel, RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.storage_panel import read_storage_view_model


def _working_save(*, source_commit_id: str | None = None) -> WorkingSaveModel:
    validation_summary = {"blocking_count": 0}
    if source_commit_id is not None:
        validation_summary["source_commit_id"] = source_commit_id
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Draft",
            updated_at="2026-04-06T00:00:00Z",
        ),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(
            status="validated",
            validation_summary=validation_summary,
            last_run={
                "run_id": "run-001",
                "status": "completed",
                "commit_id": "commit-001",
                "artifact_ids": ["artifact::output::out"],
            },
            errors=[],
        ),
        ui=UIModel(layout={}, metadata={}),
        designer=DesignerDraftModel(data={"pending": True}),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version="1.0.0",
            storage_role="commit_snapshot",
            commit_id="commit-001",
            source_working_save_id="ws-001",
            name="Approved Draft",
            updated_at="2026-04-06T01:00:00Z",
        ),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={"warning_count": 0}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={"approved_at": "2026-04-06T01:00:00Z"}),
        lineage=CommitLineageModel(parent_commit_id="commit-000", source_working_save_id="ws-001", metadata={}),
    )


def _execution() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-06T02:00:00Z",
            started_at="2026-04-06T02:00:00Z",
            finished_at="2026-04-06T02:00:05Z",
            status="completed",
            title="Run 1",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(trace_ref="trace://run-001", event_stream_ref="events://run-001"),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="out", value_summary="done")], output_summary="1 output"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="artifact::output::out", artifact_type="final_output")], artifact_count=1),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_storage_view_model_projects_complete_lifecycle_for_working_save() -> None:
    vm = read_storage_view_model(
        _working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.active_storage_role == "working_save"
    assert vm.panel_mode == "draft_focus"
    assert vm.lifecycle_summary.current_stage == "review_ready"
    assert vm.lifecycle_summary.latest_commit_id == "commit-001"
    assert vm.lifecycle_summary.latest_run_id == "run-001"
    assert vm.working_save_card is not None
    assert vm.working_save_card.can_submit_for_review is True
    assert vm.commit_snapshot_card is not None
    assert vm.execution_record_card is not None
    assert vm.relationship_graph.draft_vs_commit_status == "in_sync"
    assert any(action.action_type == "save_working_save" and action.enabled for action in vm.available_actions)
    assert any(action.action_type == "run_from_commit" and action.enabled for action in vm.available_actions)



def test_read_storage_view_model_projects_execution_focus_without_blurring_truth_domains() -> None:
    vm = read_storage_view_model(
        _execution(),
        latest_working_save=_working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
    )

    assert vm.active_storage_role == "execution_record"
    assert vm.panel_mode == "execution_focus"
    assert vm.lifecycle_summary.current_stage == "executed"
    assert vm.execution_record_card is not None
    assert vm.execution_record_card.trace_available is True
    assert vm.execution_record_card.can_open_artifacts is True
    assert vm.commit_snapshot_card is not None
    assert vm.working_save_card is not None



def test_read_storage_view_model_surfaces_stale_commit_reference_diagnostics() -> None:
    vm = read_storage_view_model(
        _working_save(source_commit_id="commit-old"),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.diagnostics.stale_reference_count >= 1
    assert vm.diagnostics.lifecycle_warning_count >= 1
    assert vm.diagnostics.last_error_label is not None



def test_read_storage_view_model_projects_working_save_only_state_without_collapsing_commit_or_run_truth() -> None:
    vm = read_storage_view_model(_working_save(), latest_commit_snapshot=None, latest_execution_record=None)

    assert vm.active_storage_role == "working_save"
    assert vm.panel_mode == "draft_focus"
    assert vm.lifecycle_summary.has_working_save is True
    assert vm.lifecycle_summary.has_latest_commit_snapshot is False
    assert vm.lifecycle_summary.has_latest_execution_record is False
    assert vm.relationship_graph.draft_vs_commit_status == "no_commit"
    assert any(action.action_type == "compare_draft_to_commit" and action.enabled is False for action in vm.available_actions)



def test_read_storage_view_model_projects_commit_only_state_as_approved_non_editable_truth() -> None:
    vm = read_storage_view_model(_commit(), latest_working_save=None, latest_execution_record=None)

    assert vm.active_storage_role == "commit_snapshot"
    assert vm.panel_mode == "commit_focus"
    assert vm.lifecycle_summary.current_stage == "approved"
    assert vm.working_save_card is None
    assert vm.commit_snapshot_card is not None
    assert vm.execution_record_card is None
    assert vm.relationship_graph.draft_vs_commit_status is None



def test_read_storage_view_model_projects_execution_only_state_as_history_first_without_fabricating_commit_card() -> None:
    vm = read_storage_view_model(_execution(), latest_working_save=None, latest_commit_snapshot=None)

    assert vm.active_storage_role == "execution_record"
    assert vm.panel_mode == "execution_focus"
    assert vm.lifecycle_summary.current_stage == "executed"
    assert vm.working_save_card is None
    assert vm.commit_snapshot_card is None
    assert vm.execution_record_card is not None
    assert vm.execution_record_card.commit_id == "commit-001"



def test_read_storage_view_model_projects_lifecycle_overview_from_latest_refs_without_collapsing_role_truth() -> None:
    vm = read_storage_view_model(
        None,
        latest_working_save=_working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.active_storage_role == "none"
    assert vm.panel_mode == "lifecycle_overview"
    assert vm.working_save_card is not None
    assert vm.commit_snapshot_card is not None
    assert vm.execution_record_card is not None
    assert vm.lifecycle_summary.has_working_save is True
    assert vm.lifecycle_summary.has_latest_commit_snapshot is True
    assert vm.lifecycle_summary.has_latest_execution_record is True



def test_read_storage_view_model_surfaces_missing_run_reference_when_working_save_points_to_unloaded_run() -> None:
    vm = read_storage_view_model(
        _working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
        latest_execution_record=None,
    )

    assert vm.diagnostics.missing_run_ref_count == 1
    assert vm.execution_record_card is None



def test_read_storage_view_model_surfaces_missing_commit_reference_when_working_save_points_to_unloaded_commit() -> None:
    vm = read_storage_view_model(
        _working_save(),
        latest_commit_snapshot=None,
        latest_execution_record=None,
    )

    assert vm.diagnostics.missing_commit_ref_count == 1
    assert vm.commit_snapshot_card is None



def test_read_storage_view_model_surfaces_resume_revalidation_warning_without_collapsing_storage_roles() -> None:
    working_save = _working_save(source_commit_id="commit-001")
    working_save = WorkingSaveModel(
        meta=working_save.meta,
        circuit=working_save.circuit,
        resources=working_save.resources,
        state=working_save.state,
        runtime=RuntimeModel(
            status=working_save.runtime.status,
            validation_summary=working_save.runtime.validation_summary,
            last_run={**working_save.runtime.last_run, "resume_ready": False},
            errors=working_save.runtime.errors,
        ),
        ui=working_save.ui,
        designer=working_save.designer,
    )

    vm = read_storage_view_model(
        working_save,
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.diagnostics.lifecycle_warning_count >= 1
    assert vm.diagnostics.last_error_label is not None
    assert vm.active_storage_role == "working_save"
    assert vm.commit_snapshot_card is not None
    assert vm.execution_record_card is not None



def test_read_storage_view_model_marks_compare_runs_enabled_only_when_second_run_exists() -> None:
    base_vm = read_storage_view_model(
        _execution(),
        latest_working_save=_working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
        recent_run_refs=["execution_record:run-001"],
    )
    enabled_vm = read_storage_view_model(
        _execution(),
        latest_working_save=_working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
        recent_run_refs=["execution_record:run-001", "execution_record:run-002"],
    )

    disabled_action = next(action for action in base_vm.available_actions if action.action_type == "compare_runs")
    enabled_action = next(action for action in enabled_vm.available_actions if action.action_type == "compare_runs")

    assert disabled_action.enabled is False
    assert enabled_action.enabled is True



def test_read_storage_view_model_uses_app_language_from_working_save_ui_metadata_for_storage_labels() -> None:
    working_save = _working_save(source_commit_id="commit-001")
    working_save = WorkingSaveModel(
        meta=working_save.meta,
        circuit=working_save.circuit,
        resources=working_save.resources,
        state=working_save.state,
        runtime=working_save.runtime,
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
        designer=working_save.designer,
    )

    vm = read_storage_view_model(
        working_save,
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.lifecycle_summary.summary_label == "드래프트가 검토 준비 상태입니다"
    save_action = next(action for action in vm.available_actions if action.action_type == "save_working_save")
    assert save_action.label == "드래프트 저장"


def test_storage_view_enables_trace_action_when_execution_record_has_event_count_without_trace_ref() -> None:
    from dataclasses import replace
    from src.storage.models.execution_record_model import ExecutionTimelineModel

    record = replace(
        _execution(),
        timeline=ExecutionTimelineModel(total_duration_ms=None, event_count=3, node_order=[], started_nodes=[], completed_nodes=[], trace_ref=None, event_stream_ref=None),
    )

    vm = read_storage_view_model(record, latest_working_save=None, latest_commit_snapshot=None)

    assert vm.execution_record_card is not None
    assert vm.execution_record_card.trace_available is True
    trace_action = next(action for action in vm.available_actions if action.action_type == "open_trace")
    assert trace_action.enabled is True
