from __future__ import annotations

import json

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE, WORKING_SAVE_ROLE
from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.serialization import (
    save_nex_artifact_file,
    save_execution_record_file,
    serialize_commit_snapshot,
    serialize_nex_artifact,
    serialize_working_save,
    validate_serialized_storage_artifact_for_write,
)
from tests.test_execution_record_api import make_snapshot


def make_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version='1.0.0', storage_role=WORKING_SAVE_ROLE, working_save_id='ws-1'),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status='draft'),
        ui=UIModel(layout={}, metadata={}),
    )


def make_commit_snapshot() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version='1.0.0', storage_role=COMMIT_SNAPSHOT_ROLE, commit_id='cs-1'),
        circuit=CircuitModel(nodes=[{'id': 'n1'}], edges=[], entry='n1', outputs=[{'name': 'out', 'source': 'n1'}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result='passed'),
        approval=CommitApprovalModel(approval_completed=True, approval_status='approved'),
        lineage=CommitLineageModel(),
    )


def test_serialize_working_save_includes_role():
    payload = serialize_working_save(make_working_save())
    assert payload['meta']['storage_role'] == WORKING_SAVE_ROLE
    assert payload['meta']['working_save_id'] == 'ws-1'


def test_serialize_commit_snapshot_includes_role():
    payload = serialize_commit_snapshot(make_commit_snapshot())
    assert payload['meta']['storage_role'] == COMMIT_SNAPSHOT_ROLE
    assert payload['meta']['commit_id'] == 'cs-1'


def test_serialize_nex_artifact_accepts_dict():
    payload = serialize_nex_artifact({'meta': {'storage_role': WORKING_SAVE_ROLE}})
    assert payload['meta']['storage_role'] == WORKING_SAVE_ROLE


def test_save_nex_artifact_file_writes_json(tmp_path):
    path = save_nex_artifact_file(make_commit_snapshot(), tmp_path / 'artifact.nex')
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['meta']['commit_id'] == 'cs-1'
    assert data['meta']['storage_role'] == COMMIT_SNAPSHOT_ROLE



def test_validate_serialized_storage_artifact_for_write_rejects_incomplete_working_save():
    try:
        validate_serialized_storage_artifact_for_write({
            'meta': {'storage_role': WORKING_SAVE_ROLE, 'working_save_id': 'ws-1'},
            'circuit': {},
            'resources': {},
            'state': {},
        })
    except ValueError as exc:
        assert 'Working Save write payload missing required object section' in str(exc)
    else:
        raise AssertionError('Expected ValueError for incomplete Working Save payload')


def test_save_nex_artifact_file_rejects_invalid_commit_snapshot_dict(tmp_path):
    invalid = {
        'meta': {'storage_role': COMMIT_SNAPSHOT_ROLE, 'commit_id': 'cs-1'},
        'circuit': {},
        'resources': {'prompts': {}, 'providers': {}, 'plugins': {}},
        'state': {'input': {}, 'working': {}, 'memory': {}},
        'validation': {'validation_result': 'passed_with_findings'},
        'approval': {'approval_completed': True, 'approval_status': 'approved'},
        'lineage': {},
    }
    try:
        save_nex_artifact_file(invalid, tmp_path / 'invalid.nex')
    except ValueError as exc:
        assert 'validation.validation_result' in str(exc)
    else:
        raise AssertionError('Expected ValueError for invalid Commit Snapshot write payload')



def test_save_execution_record_file_accepts_wrapper_payload_and_writes_canonical_record(tmp_path):
    payload = {
        'replay_payload': {
            'execution_id': 'run-123',
            'commit_id': 'commit-123',
            'node_order': ['node_a'],
            'expected_outputs': {'node_a': {'value': 'ok'}},
        },
        'result': {
            'status': 'success',
            'state': {'node_a': {'value': 'ok'}},
            'node_results': {
                'node_a': {'status': 'success', 'output': {'value': 'ok'}},
            },
        },
        'trace': {'events': ['started', 'completed']},
    }

    path = save_execution_record_file(payload, tmp_path / 'run_123.json')
    data = json.loads(path.read_text(encoding='utf-8'))

    assert data['meta']['run_id'] == 'run-123'
    assert data['source']['commit_id'] == 'commit-123'
    assert data['timeline']['event_stream_ref'] == 'events://run-123'



def test_save_nex_artifact_file_unwraps_nested_valid_execution_record_payload(tmp_path):
    record = save_execution_record_file(
        {
            'replay_payload': {
                'execution_id': 'run-xyz',
                'commit_id': 'commit-xyz',
                'node_order': ['node_a'],
                'expected_outputs': {'node_a': {'value': 'ok'}},
            },
            'result': {
                'status': 'success',
                'state': {'node_a': {'value': 'ok'}},
                'node_results': {
                    'node_a': {'status': 'success', 'output': {'value': 'ok'}},
                },
            },
            'trace': {'events': ['started', 'completed']},
        },
        tmp_path / 'seed.json',
    )
    seeded = json.loads(record.read_text(encoding='utf-8'))

    wrapped = {'execution_record': seeded, 'replay_payload': {'execution_id': 'stale-id'}}
    path = save_nex_artifact_file(wrapped, tmp_path / 'wrapped.json')
    data = json.loads(path.read_text(encoding='utf-8'))

    assert data['meta']['run_id'] == 'run-xyz'
    assert data['source']['commit_id'] == 'commit-xyz'
    assert 'execution_record' not in data
