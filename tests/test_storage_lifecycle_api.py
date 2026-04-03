from __future__ import annotations

import pytest

from src.circuit.fingerprint import compute_execution_surface_fingerprint
from src.engine.execution_artifact_hashing import ExecutionHashReport
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.engine.paused_run_state import PausedRunState
from src.storage.execution_record_api import create_execution_record_from_snapshot
from src.storage.lifecycle_api import (
    _validate_paused_run_resume_anchor,
    apply_execution_record_to_working_save,
    create_commit_snapshot_from_working_save,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel


def make_working_save(
    *,
    entry: str | None = 'n1',
    outputs: list[dict] | None = None,
    node_ids: list[str] | None = None,
    source_commit_id: str | None = None,
    providers: dict | None = None,
    prompts: dict | None = None,
    plugins: dict | None = None,
) -> WorkingSaveModel:
    resolved_node_ids = node_ids if node_ids is not None else ['n1']
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version='1.0.0',
            storage_role='working_save',
            name='Draft',
            working_save_id='ws-1',
        ),
        circuit=CircuitModel(
            nodes=[{'id': node_id} for node_id in resolved_node_ids],
            edges=[],
            entry=entry,
            outputs=outputs if outputs is not None else [{'name': 'out', 'source': 'n1'}],
        ),
        resources=ResourcesModel(
            prompts=prompts or {},
            providers=providers or {},
            plugins=plugins or {},
        ),
        state=StateModel(input={'question': 'What is AI?'}, working={}, memory={}),
        runtime=RuntimeModel(
            status='validated',
            validation_summary={
                'blocking_count': 0,
                **({'source_commit_id': source_commit_id} if source_commit_id else {}),
            },
        ),
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


def test_apply_execution_record_to_working_save_propagates_pause_boundary_summary():
    working = make_working_save(entry='node_b', outputs=[{'name': 'out', 'source': 'node_b'}], node_ids=['node_b'], source_commit_id='cs-1')
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='cs-1',
        status='paused',
        termination_reason='review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'node_b',
            'resume_from_node_id': 'node_b',
            'resume_strategy': 'restart_from_node',
            'requires_revalidation': ['structural_validation'],
        },
    )
    updated = apply_execution_record_to_working_save(working, record)
    assert updated.runtime.last_run['termination_reason'] == 'review_required'
    assert updated.runtime.last_run['pause_boundary']['pause_node_id'] == 'node_b'
    assert updated.runtime.last_run['pause_boundary']['resume_from_node_id'] == 'node_b'
    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert any(issue['code'] == 'PAUSED_RUN_EXECUTION_SURFACE_FINGERPRINT_MISSING' for issue in validation['issues'])
    assert any(issue['code'] == 'PAUSED_RUN_RESUME_REQUEST_EXECUTION_SURFACE_FINGERPRINT_MISSING' for issue in validation['issues'])
    assert any(issue['code'] == 'PAUSED_RUN_SOURCE_COMMIT_ID_MISSING' for issue in validation['issues'])
    assert any(issue['code'] == 'PAUSED_RUN_RESUME_REQUEST_SOURCE_COMMIT_ID_MISSING' for issue in validation['issues'])


def test_apply_execution_record_to_working_save_propagates_paused_run_state_and_resume_request_summary():
    working = make_working_save(source_commit_id='commit-1')
    execution_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {
            'providers': {},
            'prompts': {},
            'plugins': {},
        },
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset(),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=execution_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['paused_run_state']['paused_execution_id'] == 'exec-paused'
    assert updated.runtime.last_run['paused_run_state']['paused_node_id'] == 'n1'
    assert updated.runtime.last_run['paused_run_state']['source_commit_id'] == 'commit-1'
    assert updated.runtime.last_run['resume_request']['resume_from_node_id'] == 'n1'
    assert updated.runtime.last_run['resume_request']['previous_execution_id'] == 'exec-paused'
    assert updated.runtime.last_run['resume_request']['requires_revalidation'] == ['structural_validation', 'determinism_pre_validation']
    assert updated.runtime.last_run['resume_request']['source_commit_id'] == 'commit-1'
    assert updated.runtime.last_run['resume_ready'] is True


def test_apply_execution_record_to_working_save_recomputes_resume_ready_false_when_paused_node_missing_in_current_circuit():
    working = make_working_save(node_ids=['n_current'], source_commit_id='commit-1')
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n_missing',
        completed_node_ids=frozenset(),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=compute_execution_surface_fingerprint({
            'circuit': {
                'nodes': [{'id': 'n_current'}],
                'edges': [],
                'entry': 'n1',
                'outputs': [{'name': 'out', 'source': 'n1'}],
            },
            'resources': {'providers': {}, 'prompts': {}, 'plugins': {}},
        }),
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n_missing',
            'resume_from_node_id': 'n_missing',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert validation['effective_resume_ready'] is False
    assert any(issue['code'] == 'PAUSED_RUN_ANCHOR_NODE_MISSING' for issue in validation['issues'])


def test_apply_execution_record_to_working_save_recomputes_resume_ready_false_when_completed_boundary_is_stale():
    working = make_working_save(node_ids=['n1'], source_commit_id='commit-1')
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_stale'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=compute_execution_surface_fingerprint({
            'circuit': {
                'nodes': [{'id': 'n1'}],
                'edges': [],
                'entry': 'n1',
                'outputs': [{'name': 'out', 'source': 'n1'}],
            },
            'resources': {'providers': {}, 'prompts': {}, 'plugins': {}},
        }),
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert any(issue['code'] == 'PAUSED_RUN_COMPLETED_BOUNDARY_STALE' for issue in validation['issues'])


def test_apply_execution_record_to_working_save_keeps_resume_ready_true_when_current_circuit_matches_paused_boundary():
    working = make_working_save(node_ids=['n_done', 'n1'], source_commit_id='commit-1')
    execution_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n_done'}, {'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {
            'providers': {},
            'prompts': {},
            'plugins': {},
        },
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        execution_surface_fingerprint=execution_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is True
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is True
    assert validation['effective_resume_ready'] is True
    assert validation['issues'] == []


def test_apply_execution_record_to_working_save_recomputes_resume_ready_false_on_commit_anchor_mismatch():
    working = make_working_save(node_ids=['n_done', 'n1'], source_commit_id='commit-current')
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-stale',
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-stale',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert validation['working_save_commit_anchor_id'] == 'commit-current'
    assert any(issue['code'] == 'PAUSED_RUN_WORKING_SAVE_COMMIT_ANCHOR_MISMATCH' for issue in validation['issues'])


def test_validate_paused_run_resume_anchor_recomputes_resume_ready_false_when_paused_source_commit_missing():
    working = make_working_save(node_ids=['n_done', 'n1'], source_commit_id='commit-1')
    execution_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n_done'}, {'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {'providers': {}, 'prompts': {}, 'plugins': {}},
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=execution_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )
    updated = apply_execution_record_to_working_save(working, record)
    updated.runtime.last_run['paused_run_state']['source_commit_id'] = None

    validation = _validate_paused_run_resume_anchor(working, record, updated.runtime.last_run)

    assert validation is not None
    assert validation['anchor_valid'] is False
    assert validation['effective_resume_ready'] is False
    assert any(issue['code'] == 'PAUSED_RUN_SOURCE_COMMIT_ID_MISSING' for issue in validation['issues'])


def test_validate_paused_run_resume_anchor_recomputes_resume_ready_false_when_resume_request_source_commit_missing():
    working = make_working_save(node_ids=['n_done', 'n1'], source_commit_id='commit-1')
    execution_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n_done'}, {'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {'providers': {}, 'prompts': {}, 'plugins': {}},
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=execution_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )
    updated = apply_execution_record_to_working_save(working, record)
    updated.runtime.last_run['resume_request']['source_commit_id'] = None

    validation = _validate_paused_run_resume_anchor(working, record, updated.runtime.last_run)

    assert validation is not None
    assert validation['anchor_valid'] is False
    assert validation['effective_resume_ready'] is False
    assert any(issue['code'] == 'PAUSED_RUN_RESUME_REQUEST_SOURCE_COMMIT_ID_MISSING' for issue in validation['issues'])



def test_apply_execution_record_to_working_save_recomputes_resume_ready_false_when_execution_surface_fingerprint_missing():
    working = make_working_save(node_ids=['n_done', 'n1'], source_commit_id='commit-1')
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert any(issue['code'] == 'PAUSED_RUN_EXECUTION_SURFACE_FINGERPRINT_MISSING' for issue in validation['issues'])
    assert any(issue['code'] == 'PAUSED_RUN_RESUME_REQUEST_EXECUTION_SURFACE_FINGERPRINT_MISSING' for issue in validation['issues'])


def test_apply_execution_record_to_working_save_recomputes_resume_ready_false_on_execution_surface_fingerprint_mismatch():
    working = make_working_save(
        node_ids=['n_done', 'n1'],
        source_commit_id='commit-1',
        providers={'prov.main': {'model': 'claude-3'}},
        prompts={'p.main': {'template': 'draft'}},
    )
    paused_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n_done'}, {'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {
            'providers': {'prov.main': {'model': 'gpt-4'}},
            'prompts': {'p.main': {'template': 'draft'}},
            'plugins': {},
        },
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=paused_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert any(issue['code'] == 'PAUSED_RUN_EXECUTION_SURFACE_FINGERPRINT_MISMATCH' for issue in validation['issues'])


def test_apply_execution_record_to_working_save_keeps_resume_ready_true_when_execution_surface_matches():
    providers = {'prov.main': {'model': 'gpt-4'}}
    prompts = {'p.main': {'template': 'draft'}}
    working = make_working_save(
        node_ids=['n_done', 'n1'],
        source_commit_id='commit-1',
        providers=providers,
        prompts=prompts,
    )
    paused_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n_done'}, {'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {
            'providers': providers,
            'prompts': prompts,
            'plugins': {},
        },
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=paused_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['resume_ready'] is True
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is True
    assert validation['effective_resume_ready'] is True


def test_apply_execution_record_to_working_save_keeps_replay_run_distinct_from_resume_ready():
    working = make_working_save(node_ids=['n_done', 'n1'], source_commit_id='commit-1')
    execution_surface = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [{'id': 'n_done'}, {'id': 'n1'}],
            'edges': [],
            'entry': 'n1',
            'outputs': [{'name': 'out', 'source': 'n1'}],
        },
        'resources': {'providers': {}, 'prompts': {}, 'plugins': {}},
    })
    paused_run_state = PausedRunState.build(
        paused_execution_id='exec-paused',
        paused_node_id='n1',
        completed_node_ids=frozenset({'n_done'}),
        review_required={'reason': 'human_review_required'},
        source_commit_id='commit-1',
        execution_surface_fingerprint=execution_surface,
    )
    record = create_execution_record_from_snapshot(
        make_snapshot(status='partial'),
        commit_id='commit-1',
        trigger_type='replay_run',
        status='paused',
        termination_reason='human_review_required',
        pause_boundary={
            'can_resume': True,
            'pause_node_id': 'n1',
            'resume_from_node_id': 'n1',
            'resume_strategy': 'restart_from_node',
        },
        paused_run_state=paused_run_state,
    )

    updated = apply_execution_record_to_working_save(working, record)

    assert updated.runtime.last_run['trigger_type'] == 'replay_run'
    assert updated.runtime.last_run['replay_run'] is True
    assert updated.runtime.last_run['resume_ready'] is False
    validation = updated.runtime.last_run['resume_anchor_validation']
    assert validation['anchor_valid'] is False
    assert any(issue['code'] == 'PAUSED_RUN_REPLAY_TRIGGER_CONFLICT' for issue in validation['issues'])
