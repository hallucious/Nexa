from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.storage.execution_record_api import summarize_execution_record_for_working_save
from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.working_save_model import RuntimeModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.validators.shared_validator import validate_working_save


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_commit_snapshot_from_working_save(
    working_save: WorkingSaveModel,
    *,
    commit_id: str,
    parent_commit_id: str | None = None,
    approval_status: str = 'approved',
    approval_summary: dict | None = None,
    validation_result: str = 'passed',
    validation_summary: dict | None = None,
    created_at: str | None = None,
) -> CommitSnapshotModel:
    report = validate_working_save(working_save)
    if report.blocking_count:
        raise ValueError('Cannot create Commit Snapshot from Working Save with blocking validation findings')
    timestamp = created_at or _iso_now()
    summary = validation_summary if validation_summary is not None else {
        'warning_count': report.warning_count,
        'finding_count': len(report.findings),
    }
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version=working_save.meta.format_version,
            storage_role='commit_snapshot',
            name=working_save.meta.name,
            description=working_save.meta.description,
            created_at=working_save.meta.created_at,
            updated_at=timestamp,
            commit_id=commit_id,
            source_working_save_id=working_save.meta.working_save_id,
        ),
        circuit=working_save.circuit,
        resources=working_save.resources,
        state=working_save.state,
        validation=CommitValidationModel(
            validation_result=validation_result,
            summary=summary,
        ),
        approval=CommitApprovalModel(
            approval_completed=True,
            approval_status=approval_status,
            summary=approval_summary or {'approved_at': timestamp},
        ),
        lineage=CommitLineageModel(
            parent_commit_id=parent_commit_id,
            source_working_save_id=working_save.meta.working_save_id,
            metadata={},
        ),
    )


_SUCCESS_STATUSES = {'completed'}
_FAILURE_STATUSES = {'failed', 'partial', 'cancelled'}


def apply_execution_record_to_working_save(
    working_save: WorkingSaveModel,
    execution_record: ExecutionRecordModel,
) -> WorkingSaveModel:
    last_run = summarize_execution_record_for_working_save(execution_record)
    prior_errors = list(working_save.runtime.errors)
    status = working_save.runtime.status
    if execution_record.meta.status in _SUCCESS_STATUSES:
        status = 'executed'
        errors: list[dict] = []
    elif execution_record.meta.status in _FAILURE_STATUSES:
        status = 'execution_failed'
        errors = [
            {
                'issue_code': issue.issue_code,
                'category': issue.category,
                'severity': issue.severity,
                'location': issue.location,
                'message': issue.message,
                'reason': issue.reason,
                'fix_hint': issue.fix_hint,
            }
            for issue in execution_record.diagnostics.errors
        ]
        if not errors and prior_errors:
            errors = prior_errors
    else:
        errors = prior_errors

    runtime = RuntimeModel(
        status=status,
        validation_summary=working_save.runtime.validation_summary,
        last_run=last_run,
        errors=errors,
    )
    meta = WorkingSaveMeta(
        format_version=working_save.meta.format_version,
        storage_role=working_save.meta.storage_role,
        name=working_save.meta.name,
        description=working_save.meta.description,
        created_at=working_save.meta.created_at,
        updated_at=_iso_now(),
        working_save_id=working_save.meta.working_save_id,
    )
    return replace(working_save, meta=meta, runtime=runtime)


__all__ = [
    'create_commit_snapshot_from_working_save',
    'apply_execution_record_to_working_save',
]
