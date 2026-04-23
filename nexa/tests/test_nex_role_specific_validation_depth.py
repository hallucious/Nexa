from __future__ import annotations

from src.contracts.nex_contract import COMMIT_SNAPSHOT_ROLE, WORKING_SAVE_ROLE
from src.storage.validators.shared_validator import load_nex, validate_commit_snapshot, validate_working_save


def test_working_save_validation_is_permissive_but_flags_missing_entry_and_outputs():
    data = {
        'meta': {'format_version': '1.0.0', 'storage_role': WORKING_SAVE_ROLE, 'working_save_id': 'ws-1'},
        'circuit': {'nodes': [], 'edges': [], 'entry': None, 'outputs': []},
        'resources': {'prompts': {}, 'providers': {}, 'plugins': {}},
        'state': {'input': {}, 'working': {}, 'memory': {}},
        'runtime': {'status': 'draft'},
        'ui': {},
    }
    report = validate_working_save(data)
    assert report.role == WORKING_SAVE_ROLE
    assert report.blocking_count >= 2
    artifact = load_nex(data)
    assert artifact.storage_role == WORKING_SAVE_ROLE
    assert artifact.parsed_model is not None
    assert artifact.load_status == 'loaded_with_findings'


def test_commit_snapshot_validation_rejects_missing_entry_and_outputs():
    data = {
        'meta': {'format_version': '1.0.0', 'storage_role': COMMIT_SNAPSHOT_ROLE, 'commit_id': 'cs-1'},
        'circuit': {'nodes': [], 'edges': [], 'entry': None, 'outputs': []},
        'resources': {'prompts': {}, 'providers': {}, 'plugins': {}},
        'state': {'input': {}, 'working': {}, 'memory': {}},
        'validation': {'validation_result': 'passed'},
        'approval': {'approval_completed': True, 'approval_status': 'approved'},
        'lineage': {},
    }
    report = validate_commit_snapshot(data)
    assert report.role == COMMIT_SNAPSHOT_ROLE
    assert report.result == 'failed'
    artifact = load_nex(data)
    assert artifact.storage_role == COMMIT_SNAPSHOT_ROLE
    assert artifact.parsed_model is None
    assert artifact.load_status == 'rejected'
