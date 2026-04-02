from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.contracts.commit_snapshot_contract import (
    COMMIT_SNAPSHOT_ALLOWED_VALIDATION_RESULTS,
    COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS,
    COMMIT_SNAPSHOT_IDENTITY_FIELD,
    COMMIT_SNAPSHOT_REQUIRED_SECTIONS,
)
from src.contracts.nex_contract import ALLOWED_STORAGE_ROLES, COMMIT_SNAPSHOT_ROLE, WORKING_SAVE_ROLE
from src.contracts.working_save_contract import (
    WORKING_SAVE_ALLOWED_RUNTIME_STATUSES,
    WORKING_SAVE_IDENTITY_FIELD,
    WORKING_SAVE_REQUIRED_SECTIONS,
)
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.models.execution_record_model import ExecutionRecordModel


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _drop_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none(v) for v in value]
    return value


def _ensure_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError('Serialized .nex artifact must be a mapping at the top level')
    return value



def _validate_serialized_working_save_for_write(payload: dict[str, Any]) -> None:
    missing = [section for section in WORKING_SAVE_REQUIRED_SECTIONS if section not in payload or not isinstance(payload.get(section), dict)]
    if missing:
        raise ValueError(f"Working Save write payload missing required object section(s): {', '.join(missing)}")
    meta = payload.get('meta', {})
    if meta.get('storage_role') != WORKING_SAVE_ROLE:
        raise ValueError('Working Save write payload must declare meta.storage_role=working_save')
    if not isinstance(meta.get(WORKING_SAVE_IDENTITY_FIELD), str) or not meta.get(WORKING_SAVE_IDENTITY_FIELD):
        raise ValueError('Working Save write payload must include non-empty meta.working_save_id')
    status = payload.get('runtime', {}).get('status')
    if status is not None and status not in WORKING_SAVE_ALLOWED_RUNTIME_STATUSES:
        raise ValueError(f"Working Save write payload has unsupported runtime.status: {status}")


def _validate_serialized_commit_snapshot_for_write(payload: dict[str, Any]) -> None:
    missing = [section for section in COMMIT_SNAPSHOT_REQUIRED_SECTIONS if section not in payload or not isinstance(payload.get(section), dict)]
    if missing:
        raise ValueError(f"Commit Snapshot write payload missing required object section(s): {', '.join(missing)}")
    forbidden_present = [section for section in COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS if section in payload]
    if forbidden_present:
        raise ValueError(f"Commit Snapshot write payload must not include forbidden section(s): {', '.join(forbidden_present)}")
    meta = payload.get('meta', {})
    if meta.get('storage_role') != COMMIT_SNAPSHOT_ROLE:
        raise ValueError('Commit Snapshot write payload must declare meta.storage_role=commit_snapshot')
    if not isinstance(meta.get(COMMIT_SNAPSHOT_IDENTITY_FIELD), str) or not meta.get(COMMIT_SNAPSHOT_IDENTITY_FIELD):
        raise ValueError('Commit Snapshot write payload must include non-empty meta.commit_id')
    validation_result = payload.get('validation', {}).get('validation_result')
    if validation_result not in COMMIT_SNAPSHOT_ALLOWED_VALIDATION_RESULTS:
        raise ValueError(
            'Commit Snapshot write payload must include validation.validation_result in ' +
            str(sorted(COMMIT_SNAPSHOT_ALLOWED_VALIDATION_RESULTS))
        )
    approval_completed = payload.get('approval', {}).get('approval_completed')
    if approval_completed is not True:
        raise ValueError('Commit Snapshot write payload must include approval.approval_completed=true')
    approval_status = payload.get('approval', {}).get('approval_status')
    if not isinstance(approval_status, str) or not approval_status:
        raise ValueError('Commit Snapshot write payload must include non-empty approval.approval_status')


def _validate_serialized_execution_record_for_write(payload: dict[str, Any]) -> None:
    required_sections = (
        'meta', 'source', 'input', 'timeline', 'node_results', 'outputs', 'artifacts', 'diagnostics', 'observability'
    )
    missing = [section for section in required_sections if section not in payload or not isinstance(payload.get(section), dict)]
    if missing:
        raise ValueError(f"Execution Record write payload missing required object section(s): {', '.join(missing)}")
    meta = payload.get('meta', {})
    source = payload.get('source', {})
    if not isinstance(meta.get('run_id'), str) or not meta.get('run_id'):
        raise ValueError('Execution Record write payload must include non-empty meta.run_id')
    if not isinstance(source.get('commit_id'), str) or not source.get('commit_id'):
        raise ValueError('Execution Record write payload must include non-empty source.commit_id')


def validate_serialized_storage_artifact_for_write(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError('Storage artifact write payload must be a mapping')
    meta = payload.get('meta', {})
    storage_role = meta.get('storage_role') if isinstance(meta, dict) else None
    if storage_role is not None:
        if storage_role not in ALLOWED_STORAGE_ROLES:
            raise ValueError(f"Unsupported meta.storage_role for write payload: {storage_role}")
        if storage_role == WORKING_SAVE_ROLE:
            _validate_serialized_working_save_for_write(payload)
        elif storage_role == COMMIT_SNAPSHOT_ROLE:
            _validate_serialized_commit_snapshot_for_write(payload)
        return payload
    if 'source' in payload or 'run_id' in meta:
        _validate_serialized_execution_record_for_write(payload)
        return payload
    raise ValueError('Unrecognized storage artifact payload for write validation')


def serialize_working_save(model: WorkingSaveModel) -> dict[str, Any]:
    if not isinstance(model, WorkingSaveModel):
        raise TypeError('serialize_working_save expects WorkingSaveModel')
    return _ensure_mapping(_drop_none(asdict(model)))


def serialize_commit_snapshot(model: CommitSnapshotModel) -> dict[str, Any]:
    if not isinstance(model, CommitSnapshotModel):
        raise TypeError('serialize_commit_snapshot expects CommitSnapshotModel')
    return _ensure_mapping(_drop_none(asdict(model)))


def serialize_execution_record(model: ExecutionRecordModel) -> dict[str, Any]:
    if not isinstance(model, ExecutionRecordModel):
        raise TypeError('serialize_execution_record expects ExecutionRecordModel')
    return _ensure_mapping(_drop_none(asdict(model)))


def serialize_nex_artifact(model: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(model, WorkingSaveModel):
        return serialize_working_save(model)
    if isinstance(model, CommitSnapshotModel):
        return serialize_commit_snapshot(model)
    if isinstance(model, ExecutionRecordModel):
        return serialize_execution_record(model)
    if isinstance(model, dict):
        return _ensure_mapping(_drop_none(model))
    if is_dataclass(model):
        return _ensure_mapping(_drop_none(asdict(model)))
    raise TypeError('serialize_nex_artifact expects WorkingSaveModel, CommitSnapshotModel, ExecutionRecordModel, or dict')




def _looks_like_serialized_execution_record(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or not payload:
        return False
    meta = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    source = payload.get('source') if isinstance(payload.get('source'), dict) else {}
    return bool(meta.get('run_id') and source.get('commit_id'))


def _canonicalize_storage_write_payload(
    model: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | dict[str, Any],
) -> dict[str, Any]:
    payload = serialize_nex_artifact(model)
    meta = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    storage_role = meta.get('storage_role')
    if storage_role in ALLOWED_STORAGE_ROLES or _looks_like_serialized_execution_record(payload):
        return payload

    nested_record = payload.get('execution_record')
    if _looks_like_serialized_execution_record(nested_record):
        return _ensure_mapping(_drop_none(nested_record))

    if any(key in payload for key in ('execution_record', 'replay_payload', 'result', 'trace', 'summary')):
        from src.storage.execution_record_api import materialize_execution_record_from_payload

        normalized_payload = dict(payload)
        record = materialize_execution_record_from_payload(normalized_payload)
        if _looks_like_serialized_execution_record(record):
            return _ensure_mapping(_drop_none(record))

    return payload

def save_nex_artifact_file(model: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    payload = validate_serialized_storage_artifact_for_write(_canonicalize_storage_write_payload(model))
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return path


def save_execution_record_file(model: ExecutionRecordModel | dict[str, Any], destination: str | Path) -> Path:
    return save_nex_artifact_file(model, destination)


__all__ = [
    'serialize_working_save',
    'serialize_commit_snapshot',
    'serialize_execution_record',
    'serialize_nex_artifact',
    'validate_serialized_storage_artifact_for_write',
    'save_nex_artifact_file',
    'save_execution_record_file',
]
