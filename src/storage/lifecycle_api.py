from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.engine.execution_snapshot import ExecutionSnapshot
from src.storage.execution_record_api import (
    create_execution_record_from_snapshot,
    summarize_execution_record_for_working_save,
)
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


def _ensure_commit_snapshot_is_execution_ready(commit_snapshot: CommitSnapshotModel) -> None:
    if not commit_snapshot.approval.approval_completed:
        raise ValueError('Cannot create Execution Record from Commit Snapshot before approval is completed')
    if commit_snapshot.validation.validation_result not in {'passed', 'passed_with_findings'}:
        raise ValueError('Cannot create Execution Record from Commit Snapshot with failing validation result')


def _resolve_commit_snapshot_working_save_id(commit_snapshot: CommitSnapshotModel, explicit_working_save_id: str | None) -> str | None:
    if explicit_working_save_id:
        return explicit_working_save_id
    if commit_snapshot.meta.source_working_save_id:
        return commit_snapshot.meta.source_working_save_id
    if commit_snapshot.lineage.source_working_save_id:
        return commit_snapshot.lineage.source_working_save_id
    return None


def create_execution_record_from_commit_snapshot(
    snapshot: ExecutionSnapshot,
    commit_snapshot: CommitSnapshotModel,
    *,
    trigger_type: str = 'manual_run',
    working_save_id: str | None = None,
    trigger_reason: str | None = None,
    status: str = 'completed',
    title: str | None = None,
    description: str | None = None,
    created_at: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    input_summary: dict | None = None,
    input_ref: str | None = None,
    input_hash: str | None = None,
    schema_summary: str | None = None,
    trace_ref: str | None = None,
    event_stream_ref: str | None = None,
    final_outputs: dict | None = None,
    artifact_refs = None,
    warnings = None,
    errors = None,
    failure_point: str | None = None,
    termination_reason: str | None = None,
    provider_usage_summary: dict | None = None,
    plugin_usage_summary: dict | None = None,
    trace_summary: str | None = None,
    observability_refs: list[str] | None = None,
) -> ExecutionRecordModel:
    _ensure_commit_snapshot_is_execution_ready(commit_snapshot)
    resolved_working_save_id = _resolve_commit_snapshot_working_save_id(commit_snapshot, working_save_id)
    resolved_title = title or commit_snapshot.meta.name
    resolved_description = description or commit_snapshot.meta.description
    resolved_trigger_reason = trigger_reason or f'commit_snapshot:{commit_snapshot.meta.commit_id}'
    return create_execution_record_from_snapshot(
        snapshot,
        commit_id=commit_snapshot.meta.commit_id,
        trigger_type=trigger_type,
        working_save_id=resolved_working_save_id,
        trigger_reason=resolved_trigger_reason,
        status=status,
        title=resolved_title,
        description=resolved_description,
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        input_summary=input_summary,
        input_ref=input_ref,
        input_hash=input_hash,
        schema_summary=schema_summary,
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        final_outputs=final_outputs,
        artifact_refs=artifact_refs,
        warnings=warnings,
        errors=errors,
        failure_point=failure_point,
        termination_reason=termination_reason,
        provider_usage_summary=provider_usage_summary,
        plugin_usage_summary=plugin_usage_summary,
        trace_summary=trace_summary,
        observability_refs=observability_refs,
    )


def create_execution_record_and_update_working_save(
    snapshot: ExecutionSnapshot,
    commit_snapshot: CommitSnapshotModel,
    working_save: WorkingSaveModel,
    *,
    trigger_type: str = 'manual_run',
    trigger_reason: str | None = None,
    status: str = 'completed',
    title: str | None = None,
    description: str | None = None,
    created_at: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    input_summary: dict | None = None,
    input_ref: str | None = None,
    input_hash: str | None = None,
    schema_summary: str | None = None,
    trace_ref: str | None = None,
    event_stream_ref: str | None = None,
    final_outputs: dict | None = None,
    artifact_refs = None,
    warnings = None,
    errors = None,
    failure_point: str | None = None,
    termination_reason: str | None = None,
    provider_usage_summary: dict | None = None,
    plugin_usage_summary: dict | None = None,
    trace_summary: str | None = None,
    observability_refs: list[str] | None = None,
) -> tuple[ExecutionRecordModel, WorkingSaveModel]:
    expected_working_save_id = _resolve_commit_snapshot_working_save_id(commit_snapshot, None)
    if expected_working_save_id and working_save.meta.working_save_id != expected_working_save_id:
        raise ValueError('Working Save does not match Commit Snapshot source_working_save_id')
    record = create_execution_record_from_commit_snapshot(
        snapshot,
        commit_snapshot,
        trigger_type=trigger_type,
        working_save_id=working_save.meta.working_save_id,
        trigger_reason=trigger_reason,
        status=status,
        title=title,
        description=description,
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        input_summary=input_summary,
        input_ref=input_ref,
        input_hash=input_hash,
        schema_summary=schema_summary,
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        final_outputs=final_outputs,
        artifact_refs=artifact_refs,
        warnings=warnings,
        errors=errors,
        failure_point=failure_point,
        termination_reason=termination_reason,
        provider_usage_summary=provider_usage_summary,
        plugin_usage_summary=plugin_usage_summary,
        trace_summary=trace_summary,
        observability_refs=observability_refs,
    )
    return record, apply_execution_record_to_working_save(working_save, record)


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
    'create_execution_record_from_commit_snapshot',
    'create_execution_record_and_update_working_save',
    'apply_execution_record_to_working_save',
]
