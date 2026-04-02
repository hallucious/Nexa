from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.engine.execution_snapshot import ExecutionSnapshot
from src.storage.execution_record_api import (
    build_execution_record_reference_contract_from_serialized_record,
    create_execution_record_from_snapshot,
    create_serialized_execution_record_from_circuit_run,
    create_serialized_execution_record_from_savefile_trace,
    materialize_execution_record_from_payload,
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
from src.storage.serialization import (
    serialize_commit_snapshot,
    serialize_execution_record,
    serialize_working_save,
)
from src.storage.validators.shared_validator import validate_working_save


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_VALID_COMMIT_VALIDATION_RESULTS = {'passed', 'passed_with_warnings'}
_LEGACY_COMMIT_VALIDATION_RESULT_ALIASES = {'passed_with_findings': 'passed_with_warnings'}


def _normalize_commit_validation_result(value: str) -> str:
    normalized = _LEGACY_COMMIT_VALIDATION_RESULT_ALIASES.get(value, value)
    if normalized not in _VALID_COMMIT_VALIDATION_RESULTS:
        raise ValueError(
            "Commit Snapshot validation_result must be one of {'passed', 'passed_with_warnings'}"
        )
    return normalized


def _build_execution_summary(initial_state: dict | None, final_state: dict | None, started_at: float, ended_at: float) -> dict:
    duration_ms = max(0, int((ended_at - started_at) * 1000))
    initial_keys = sorted((initial_state or {}).keys())
    final_keys = sorted((final_state or {}).keys())
    return {
        "duration_ms": duration_ms,
        "initial_keys": initial_keys,
        "final_keys": final_keys,
        "state_changed": (initial_state or {}) != (final_state or {}),
    }


def create_serialized_savefile_execution_payload(
    savefile,
    trace,
    *,
    started_at: float,
    ended_at: float,
) -> dict:
    final_state = getattr(trace, "final_state", {}) or {}
    node_results = getattr(trace, "node_results", {}) or {}
    expected_outputs: dict[str, dict] = {}
    for node_id, result in node_results.items():
        expected_outputs[str(node_id)] = {
            "status": getattr(result, "status", None),
            "output": getattr(result, "output", None),
            "error": getattr(result, "error", None),
            "artifacts": getattr(result, "artifacts", []),
            "trace": getattr(result, "trace", {}),
        }

    replay_payload = {
        "execution_id": getattr(trace, "run_id", "unknown-execution"),
        "node_order": [node.id for node in getattr(savefile.circuit, "nodes", [])],
        "circuit": {
            "id": savefile.meta.name,
            "nodes": [{"id": node.id} for node in getattr(savefile.circuit, "nodes", [])],
        },
        "execution_configs": {},
        "input_state": getattr(savefile.state, "input", {}) or {},
        "expected_outputs": expected_outputs,
    }

    payload = {
        "result": {
            "state": final_state,
            "status": getattr(trace, "status", None),
            "node_results": expected_outputs,
            "artifacts": getattr(trace, "all_artifacts", []),
        },
        "summary": _build_execution_summary(
            getattr(savefile.state, "input", {}) or {},
            final_state,
            started_at,
            ended_at,
        ),
        "trace": {"events": []},
        "artifacts": getattr(trace, "all_artifacts", []),
        "replay_payload": replay_payload,
    }
    payload["execution_record"] = create_serialized_execution_record_from_savefile_trace(
        savefile,
        trace,
        started_at=started_at,
        ended_at=ended_at,
    )
    components = create_serialized_execution_artifact_components(payload)
    payload["execution_record"] = components['execution_record']
    payload["execution_record_reference_contract"] = components['execution_record_reference_contract']
    payload["primary_trace_ref"] = components['primary_trace_ref']
    return payload


def create_serialized_circuit_execution_payload(
    circuit: dict,
    final_state: dict,
    *,
    initial_state: dict,
    execution_configs: dict,
    started_at: float,
    ended_at: float,
    trace: dict | None = None,
    artifacts: list | None = None,
) -> dict:
    replay_payload = {
        "execution_id": circuit.get("id", "unknown-execution"),
        "node_order": [node.get("id") for node in circuit.get("nodes", []) if node.get("id")],
        "circuit": circuit,
        "execution_configs": dict(execution_configs),
        "input_state": initial_state,
        "expected_outputs": {
            node.get("id"): final_state.get(node.get("id"))
            for node in circuit.get("nodes", [])
            if node.get("id") in final_state
        },
    }
    payload = {
        "result": {"state": final_state},
        "summary": _build_execution_summary(initial_state, final_state, started_at, ended_at),
        "trace": trace or {"events": []},
        "artifacts": artifacts or [],
        "replay_payload": replay_payload,
    }
    payload["execution_record"] = create_serialized_execution_record_from_circuit_run(
        circuit,
        final_state,
        started_at=started_at,
        ended_at=ended_at,
        execution_id=str(circuit.get("id") or "unknown-execution"),
        input_state=initial_state,
        trace=payload.get("trace"),
        artifacts=payload.get("artifacts"),
    )
    components = create_serialized_execution_artifact_components(payload)
    payload["execution_record"] = components['execution_record']
    payload["execution_record_reference_contract"] = components['execution_record_reference_contract']
    payload["primary_trace_ref"] = components['primary_trace_ref']
    return payload
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
    normalized_validation_result = _normalize_commit_validation_result(validation_result)
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


def create_serialized_commit_snapshot_from_working_save(
    working_save: WorkingSaveModel,
    *,
    commit_id: str,
    parent_commit_id: str | None = None,
    approval_status: str = 'approved',
    approval_summary: dict | None = None,
    validation_result: str = 'passed',
    validation_summary: dict | None = None,
    created_at: str | None = None,
) -> dict:
    snapshot = create_commit_snapshot_from_working_save(
        working_save,
        commit_id=commit_id,
        parent_commit_id=parent_commit_id,
        approval_status=approval_status,
        approval_summary=approval_summary,
        validation_result=validation_result,
        validation_summary=validation_summary,
        created_at=created_at,
    )
    return serialize_commit_snapshot(snapshot)


def create_serialized_execution_record_from_commit_snapshot(
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
    artifact_refs=None,
    warnings=None,
    errors=None,
    failure_point: str | None = None,
    termination_reason: str | None = None,
    provider_usage_summary: dict | None = None,
    plugin_usage_summary: dict | None = None,
    trace_summary: str | None = None,
    observability_refs: list[str] | None = None,
) -> dict:
    record = create_execution_record_from_commit_snapshot(
        snapshot,
        commit_snapshot,
        trigger_type=trigger_type,
        working_save_id=working_save_id,
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
    return serialize_execution_record(record)


def create_serialized_execution_transition(
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
    artifact_refs=None,
    warnings=None,
    errors=None,
    failure_point: str | None = None,
    termination_reason: str | None = None,
    provider_usage_summary: dict | None = None,
    plugin_usage_summary: dict | None = None,
    trace_summary: str | None = None,
    observability_refs: list[str] | None = None,
) -> dict:
    record, updated_working_save = create_execution_record_and_update_working_save(
        snapshot,
        commit_snapshot,
        working_save,
        trigger_type=trigger_type,
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
    execution_record_payload = serialize_execution_record(record)
    components = create_serialized_execution_artifact_components({'execution_record': execution_record_payload})
    return {
        'execution_record': components['execution_record'],
        'updated_working_save': serialize_working_save(updated_working_save),
        'execution_record_reference_contract': components['execution_record_reference_contract'],
        'primary_trace_ref': components['primary_trace_ref'],
        'last_run_summary': dict(updated_working_save.runtime.last_run),
    }


_SUCCESS_STATUSES = {'completed'}
_FAILURE_STATUSES = {'failed', 'partial', 'cancelled'}


def _ensure_commit_snapshot_is_execution_ready(commit_snapshot: CommitSnapshotModel) -> None:
    if not commit_snapshot.approval.approval_completed:
        raise ValueError('Cannot create Execution Record from Commit Snapshot before approval is completed')
    if _normalize_commit_validation_result(commit_snapshot.validation.validation_result) not in _VALID_COMMIT_VALIDATION_RESULTS:
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
    'create_serialized_commit_snapshot_from_working_save',
    'create_execution_record_from_commit_snapshot',
    'create_serialized_execution_record_from_commit_snapshot',
    'create_execution_record_and_update_working_save',
    'create_serialized_execution_transition',
    'apply_execution_record_to_working_save',
    'create_serialized_execution_artifact_components',
    'create_serialized_audit_replay_input',
    'create_serialized_audit_export_payload',
    'create_serialized_audit_bundle_contents',
    'create_serialized_audit_replay_components',
]


def create_serialized_execution_artifact_components(payload: dict) -> dict:
    """Normalize the shared execution-artifact component surface.

    This is the smallest shared transition-builder surface reused by run/export/replay.
    Prefer native execution_record when available; otherwise fall back to storage-side
    materialization from the payload. When a native execution_record is available,
    reference-contract semantics are re-derived from that record so stale incoming
    contract dictionaries do not survive.
    """
    safe_payload = payload if isinstance(payload, dict) else {}
    native_execution_record = safe_payload.get('execution_record', {})
    has_native_execution_record = isinstance(native_execution_record, dict) and bool(native_execution_record)
    execution_record = native_execution_record if has_native_execution_record else materialize_execution_record_from_payload(safe_payload)

    if has_native_execution_record:
        reference_contract = build_execution_record_reference_contract_from_serialized_record(execution_record)
    else:
        reference_contract = safe_payload.get('execution_record_reference_contract', {})
        if not isinstance(reference_contract, dict) or not reference_contract:
            reference_contract = build_execution_record_reference_contract_from_serialized_record(execution_record)

    replay_payload = safe_payload.get('replay_payload', {})
    if not isinstance(replay_payload, dict):
        replay_payload = {}

    source = execution_record.get('source', {}) if isinstance(execution_record, dict) else {}
    meta = execution_record.get('meta', {}) if isinstance(execution_record, dict) else {}

    return {
        'run_id': meta.get('run_id'),
        'commit_id': source.get('commit_id'),
        'replay_payload': replay_payload,
        'execution_record': execution_record,
        'execution_record_reference_contract': reference_contract,
        'primary_trace_ref': reference_contract.get('primary_trace_ref'),
    }


def create_serialized_audit_replay_input(payload: dict) -> dict:
    """Normalize replay-facing serialized components from an audit payload.

    This centralizes replay input interpretation so replay consumers share the
    same storage/lifecycle transition vocabulary used by audit export.
    """
    return create_serialized_execution_artifact_components(payload if isinstance(payload, dict) else {})

def create_serialized_audit_export_payload(payload: dict) -> dict:
    """Build normalized audit-export components from a run payload.

    This centralizes storage/lifecycle-owned artifact assembly so audit/export
    consumers do not need to reconstruct execution payload semantics on their own.
    """
    safe_payload = payload if isinstance(payload, dict) else {}
    components = create_serialized_execution_artifact_components(safe_payload)

    result = safe_payload.get('result', {}) if isinstance(safe_payload.get('result'), dict) else {}
    state = result.get('state', {}) if isinstance(result, dict) else {}
    summary = safe_payload.get('summary', {}) if isinstance(safe_payload.get('summary'), dict) else {}
    trace = safe_payload.get('trace', safe_payload.get('execution_trace', {}))
    if not isinstance(trace, dict):
        trace = {}
    artifacts = safe_payload.get('artifacts', [])
    if not isinstance(artifacts, list):
        artifacts = []

    contract = components.get('execution_record_reference_contract', {})
    metadata = {
        'format': 'nexa.audit_pack',
        'version': '1.0.0',
        'artifact_count': len(artifacts),
        'state_key_count': len(state) if isinstance(state, dict) else 0,
    }
    if isinstance(contract, dict) and contract:
        metadata['replay_ready'] = bool(contract.get('is_replay_ready'))
        metadata['audit_ready'] = bool(contract.get('is_audit_ready'))
        metadata['primary_trace_ref'] = contract.get('primary_trace_ref')

    return {
        'metadata': metadata,
        'execution_trace_payload': {
            'trace': trace,
            'state': state,
        },
        'summary_payload': {
            'summary': summary,
        },
        'replay_payload': components.get('replay_payload', {}),
        'execution_record': components.get('execution_record', {}),
        'execution_record_reference_contract': contract,
        'artifacts': artifacts,
    }

def create_serialized_audit_bundle_contents(payload: dict) -> dict:
    """Build file-oriented audit bundle contents from a run payload.

    This provides a thinner, export-friendly surface so audit pack builders can
    consume storage/lifecycle-owned serialized components without reinterpreting
    the payload locally.
    """
    audit_payload = create_serialized_audit_export_payload(payload if isinstance(payload, dict) else {})
    contents = {
        'metadata.json': audit_payload.get('metadata', {}),
        'execution_trace.json': audit_payload.get('execution_trace_payload', {}),
        'summary.json': audit_payload.get('summary_payload', {}),
        'replay_payload.json': audit_payload.get('replay_payload', {}),
        'artifacts': audit_payload.get('artifacts', []),
    }
    execution_record = audit_payload.get('execution_record', {})
    if isinstance(execution_record, dict) and execution_record:
        contents['execution_record.json'] = execution_record
    reference_contract = audit_payload.get('execution_record_reference_contract', {})
    if isinstance(reference_contract, dict) and reference_contract:
        contents['execution_record_reference_contract.json'] = reference_contract
    return contents


def create_serialized_audit_replay_components(payload: dict) -> dict:
    """Build replay-facing serialized components from explicit audit inputs.

    This is intentionally file-agnostic so replay consumers can normalize input
    using the same storage/lifecycle vocabulary used by export.
    """
    return create_serialized_execution_artifact_components(payload if isinstance(payload, dict) else {})
