from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
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
from src.ui.builder_dispatch_hub import read_builder_dispatch_hub_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
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


def test_builder_dispatch_hub_integrates_interaction_emission_dispatch_and_lifecycle() -> None:
    vm = read_builder_dispatch_hub_view_model(_working_save(), interaction_hub=None)

    assert vm.interaction_hub is not None
    assert vm.intent_emission is not None
    assert vm.dispatch_contract is not None
    assert vm.lifecycle is not None
    assert vm.enabled_dispatch_count >= 1
    assert vm.hub_status_label == "주의 필요"


def test_builder_dispatch_hub_prioritizes_terminal_status_for_execution_record() -> None:
    vm = read_builder_dispatch_hub_view_model(_run())

    assert vm.source_role == "execution_record"
    assert vm.lifecycle is not None
    assert vm.lifecycle.terminal is True
    assert vm.hub_status == "terminal"


def test_builder_dispatch_hub_keeps_commit_snapshot_launch_ready() -> None:
    vm = read_builder_dispatch_hub_view_model(_commit())

    assert vm.source_role == "commit_snapshot"
    assert vm.hub_status in {"ready", "attention"}
    assert vm.recommended_action_id in {"run_from_commit", "open_latest_commit"}
