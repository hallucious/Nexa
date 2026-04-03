from __future__ import annotations

import pytest

from src.engine.execution_artifact_hashing import ExecutionHashReport
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.storage.execution_record_api import create_execution_record_from_snapshot
from src.storage.lifecycle_api import (
    apply_execution_record_to_working_save,
    create_commit_snapshot_from_working_save,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_working_save(*, entry: str | None = 'n1', outputs: list[dict] | None = None) -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version='1.0.0',
            storage_role='working_save',
            name='Draft',
            working_save_id='ws-1',
        ),
        circuit=CircuitModel(
            nodes=[{'id': 'n1'}],
            edges=[],
            entry=entry,
            outputs=outputs if outputs is not None else [{'name': 'out', 'source': 'n1'}],
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


def test_create_commit_snapshot_from_working_save_requires_non_blocking_validation():
    invalid = make_working_save(entry=None, outputs=[])
    with pytest.raises(ValueError):
        create_commit_snapshot_from_working_save(invalid, commit_id='cs-1')


def test_create_commit_snapshot_from_working_save_copies_structural_state():
    working = make_working_save()
    snapshot = create_commit_snapshot_from_working_save(working, commit_id='cs-1', parent_commit_id='cs-0')
    assert snapshot.meta.commit_id == 'cs-1'
    assert snapshot.meta.source_working_save_id == 'ws-1'
    assert snapshot.lineage.parent_commit_id == 'cs-0'
    assert snapshot.circuit.entry == 'n1'
    assert snapshot.approval.approval_completed is True


def test_apply_execution_record_to_working_save_updates_last_run_and_status_on_success():
    working = make_working_save()
    record = create_execution_record_from_snapshot(make_snapshot(), commit_id='cs-1')
    updated = apply_execution_record_to_working_save(working, record)
    assert updated.runtime.status == 'executed'
    assert updated.runtime.last_run['run_id'] == 'exec-1'
    assert updated.runtime.last_run['commit_id'] == 'cs-1'
    assert updated.runtime.errors == []


def test_apply_execution_record_to_working_save_marks_execution_failed_and_copies_errors():
    working = make_working_save()
    record = create_execution_record_from_snapshot(
        make_snapshot(status='failed'),
        commit_id='cs-1',
        status='failed',
        errors=[],
        failure_point='n1',
        termination_reason='provider timeout',
    )
    updated = apply_execution_record_to_working_save(working, record)
    assert updated.runtime.status == 'execution_failed'
    assert updated.runtime.last_run['status'] == 'failed'


def test_apply_execution_record_to_working_save_marks_execution_paused_and_preserves_summary():
    working = make_working_save()
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='cs-1',
        status='paused',
        termination_reason='review_required',
    )
    updated = apply_execution_record_to_working_save(working, record)
    assert updated.runtime.status == 'execution_paused'
    assert updated.runtime.last_run['status'] == 'paused'
    assert updated.runtime.last_run['semantic_status'] == 'paused'
    assert updated.runtime.errors == []
