from __future__ import annotations

import pytest

from src.engine.execution_artifact_hashing import ExecutionHashReport
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.storage.lifecycle_api import (
    create_commit_snapshot_from_working_save,
    create_execution_record_and_update_working_save,
    create_execution_record_from_commit_snapshot,
)
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_working_save(*, working_save_id: str = 'ws-1') -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version='1.0.0',
            storage_role='working_save',
            name='Draft',
            working_save_id=working_save_id,
        ),
        circuit=CircuitModel(
            nodes=[{'id': 'n1'}],
            edges=[],
            entry='n1',
            outputs=[{'name': 'out', 'source': 'n1'}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={'question': 'What is AI?'}, working={}, memory={}),
        runtime=RuntimeModel(status='validated', validation_summary={'blocking_count': 0}),
        ui=UIModel(layout={}, metadata={}),
    )


def make_snapshot(*, status: str = 'success'):
    timeline = ExecutionTimeline(
        execution_id='exec-1',
        start_ms=1000,
        end_ms=2000,
        duration_ms=1000,
        node_spans=[NodeExecutionSpan('n1', 1000, 2000, 1000, status)],
    )
    return ExecutionSnapshotBuilder().build(
        execution_id='exec-1',
        timeline=timeline,
        outputs={'out': {'value': 'done'}},
        hash_report=ExecutionHashReport(execution_id='exec-1', node_hashes=[]),
    )


def make_unapproved_commit_snapshot() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version='1.0.0',
            storage_role='commit_snapshot',
            name='Draft',
            commit_id='cs-1',
            source_working_save_id='ws-1',
        ),
        circuit=CircuitModel(nodes=[{'id': 'n1'}], edges=[], entry='n1', outputs=[{'name': 'out', 'source': 'n1'}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result='passed', summary={}),
        approval=CommitApprovalModel(approval_completed=False, approval_status='pending', summary={}),
        lineage=CommitLineageModel(source_working_save_id='ws-1', metadata={}),
    )


def test_create_execution_record_from_commit_snapshot_uses_snapshot_identity():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    record = create_execution_record_from_commit_snapshot(make_snapshot(), commit_snapshot)
    assert record.source.commit_id == 'cs-1'
    assert record.source.working_save_id == 'ws-1'
    assert record.meta.title == 'Draft'


def test_create_execution_record_from_commit_snapshot_rejects_unapproved_snapshot():
    with pytest.raises(ValueError):
        create_execution_record_from_commit_snapshot(make_snapshot(), make_unapproved_commit_snapshot())


def test_create_execution_record_from_commit_snapshot_rejects_failed_validation_snapshot():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1', validation_result='failed')
    with pytest.raises(ValueError):
        create_execution_record_from_commit_snapshot(make_snapshot(), commit_snapshot)


def test_create_execution_record_and_update_working_save_links_record_and_summary():
    working = make_working_save()
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    record, updated = create_execution_record_and_update_working_save(make_snapshot(), commit_snapshot, working)
    assert record.source.commit_id == 'cs-1'
    assert updated.runtime.last_run['commit_id'] == 'cs-1'
    assert updated.runtime.last_run['run_id'] == record.meta.run_id
    assert updated.runtime.status == 'executed'


def test_create_execution_record_and_update_working_save_rejects_mismatched_working_save():
    working = make_working_save(working_save_id='ws-1')
    other_working = make_working_save(working_save_id='ws-2')
    commit_snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1')
    with pytest.raises(ValueError):
        create_execution_record_and_update_working_save(make_snapshot(), commit_snapshot, other_working)
