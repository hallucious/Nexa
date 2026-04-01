from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

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
    raise TypeError('serialize_nex_artifact expects WorkingSaveModel, CommitSnapshotModel, or dict')


def save_nex_artifact_file(model: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    payload = serialize_nex_artifact(model)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return path


def save_execution_record_file(model: ExecutionRecordModel, destination: str | Path) -> Path:
    return save_nex_artifact_file(model, destination)


__all__ = [
    'serialize_working_save',
    'serialize_commit_snapshot',
    'serialize_execution_record',
    'serialize_nex_artifact',
    'save_nex_artifact_file',
    'save_execution_record_file',
]
