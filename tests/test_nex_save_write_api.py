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
    serialize_commit_snapshot,
    serialize_nex_artifact,
    serialize_working_save,
)


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
