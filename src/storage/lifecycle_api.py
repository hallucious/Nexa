from __future__ import annotations

from dataclasses import replace

from src.circuit.fingerprint import compute_circuit_fingerprint, compute_execution_surface_fingerprint
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
            validation_result=normalized_validation_result,
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
_PAUSED_STATUSES = {'paused'}
_FAILURE_STATUSES = {'failed', 'partial', 'cancelled'}


def _working_save_node_ids(working_save: WorkingSaveModel) -> set[str]:
    node_ids: set[str] = set()
    for node in getattr(working_save.circuit, 'nodes', []) or []:
        if isinstance(node, dict):
            node_id = node.get('id') or node.get('node_id')
            if isinstance(node_id, str) and node_id:
                node_ids.add(node_id)
    return node_ids


def _working_save_commit_anchor_id(working_save: WorkingSaveModel) -> str | None:
    validation_summary = (
        working_save.runtime.validation_summary
        if isinstance(getattr(working_save.runtime, 'validation_summary', None), dict)
        else {}
    )
    for key in ('source_commit_id', 'current_commit_id', 'commit_id'):
        value = validation_summary.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _validate_paused_run_resume_anchor(
    working_save: WorkingSaveModel,
    execution_record: ExecutionRecordModel,
    last_run_summary: dict[str, object],
) -> dict[str, object] | None:
    if execution_record.meta.status not in _PAUSED_STATUSES:
        return None

    node_ids = _working_save_node_ids(working_save)
    pause_boundary = last_run_summary.get('pause_boundary') if isinstance(last_run_summary.get('pause_boundary'), dict) else {}
    paused_run_state = last_run_summary.get('paused_run_state') if isinstance(last_run_summary.get('paused_run_state'), dict) else {}
    resume_request = last_run_summary.get('resume_request') if isinstance(last_run_summary.get('resume_request'), dict) else {}
    working_save_commit_anchor_id = _working_save_commit_anchor_id(working_save)

    issues: list[dict[str, str]] = []

    pause_node_id = paused_run_state.get('paused_node_id') or pause_boundary.get('pause_node_id')
    resume_from_node_id = resume_request.get('resume_from_node_id') or pause_boundary.get('resume_from_node_id')
    paused_source_commit_id = paused_run_state.get('source_commit_id') if isinstance(paused_run_state.get('source_commit_id'), str) else None
    resume_source_commit_id = resume_request.get('source_commit_id') if isinstance(resume_request.get('source_commit_id'), str) else None
    paused_structure_fingerprint = paused_run_state.get('structure_fingerprint') if isinstance(paused_run_state.get('structure_fingerprint'), str) else None
    resume_structure_fingerprint = resume_request.get('structure_fingerprint') if isinstance(resume_request.get('structure_fingerprint'), str) else None
    paused_execution_surface_fingerprint = paused_run_state.get('execution_surface_fingerprint') if isinstance(paused_run_state.get('execution_surface_fingerprint'), str) else None
    resume_execution_surface_fingerprint = resume_request.get('execution_surface_fingerprint') if isinstance(resume_request.get('execution_surface_fingerprint'), str) else None
    current_structure_fingerprint = compute_circuit_fingerprint({'nodes': [dict(node) for node in getattr(working_save.circuit, 'nodes', []) or []], 'edges': [dict(edge) for edge in getattr(working_save.circuit, 'edges', []) or []], 'entry': getattr(working_save.circuit, 'entry', None), 'outputs': [dict(output) for output in getattr(working_save.circuit, 'outputs', []) or []]})
    current_execution_surface_fingerprint = compute_execution_surface_fingerprint({
        'circuit': {
            'nodes': [dict(node) for node in getattr(working_save.circuit, 'nodes', []) or []],
            'edges': [dict(edge) for edge in getattr(working_save.circuit, 'edges', []) or []],
            'entry': getattr(working_save.circuit, 'entry', None),
            'outputs': [dict(output) for output in getattr(working_save.circuit, 'outputs', []) or []],
        },
        'resources': {
            'prompts': dict(getattr(working_save.resources, 'prompts', {}) or {}),
            'providers': dict(getattr(working_save.resources, 'providers', {}) or {}),
            'plugins': dict(getattr(working_save.resources, 'plugins', {}) or {}),
        },
    })
    record_source_commit_id = execution_record.source.commit_id

    if not paused_execution_surface_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_EXECUTION_SURFACE_FINGERPRINT_MISSING',
            'message': (
                'paused_run_state execution_surface_fingerprint is missing; '
                'resume readiness cannot be trusted without a stored execution-surface fingerprint'
            ),
        })

    if not resume_execution_surface_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_RESUME_REQUEST_EXECUTION_SURFACE_FINGERPRINT_MISSING',
            'message': (
                'resume_request execution_surface_fingerprint is missing; '
                'resume readiness cannot be trusted without a resume-request execution-surface fingerprint'
            ),
        })

    if not current_execution_surface_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_WORKING_SAVE_EXECUTION_SURFACE_FINGERPRINT_MISSING',
            'message': (
                'current Working Save execution_surface_fingerprint is missing; '
                'resume readiness cannot be trusted without a current execution-surface fingerprint'
            ),
        })

    if paused_source_commit_id and paused_source_commit_id != record_source_commit_id:
        issues.append({
            'code': 'PAUSED_RUN_SOURCE_COMMIT_MISMATCH',
            'message': (
                f"paused_run_state source_commit_id '{paused_source_commit_id}' does not match "
                f"Execution Record source commit_id '{record_source_commit_id}'"
            ),
        })

    if resume_source_commit_id and resume_source_commit_id != record_source_commit_id:
        issues.append({
            'code': 'PAUSED_RUN_RESUME_REQUEST_COMMIT_MISMATCH',
            'message': (
                f"resume_request source_commit_id '{resume_source_commit_id}' does not match "
                f"Execution Record source commit_id '{record_source_commit_id}'"
            ),
        })

    if paused_structure_fingerprint and resume_structure_fingerprint and paused_structure_fingerprint != resume_structure_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_RESUME_REQUEST_FINGERPRINT_MISMATCH',
            'message': (
                f"resume_request structure_fingerprint '{resume_structure_fingerprint}' does not match "
                f"paused_run_state structure_fingerprint '{paused_structure_fingerprint}'"
            ),
        })

    effective_source_commit_id = paused_source_commit_id or resume_source_commit_id or record_source_commit_id
    effective_structure_fingerprint = paused_structure_fingerprint or resume_structure_fingerprint

    if not working_save_commit_anchor_id:
        issues.append({
            'code': 'PAUSED_RUN_WORKING_SAVE_COMMIT_ANCHOR_MISSING',
            'message': (
                'current Working Save commit anchor is missing; resumability cannot be trusted '
                'without an explicit current commit anchor'
            ),
        })
    elif effective_source_commit_id and working_save_commit_anchor_id != effective_source_commit_id:
        issues.append({
            'code': 'PAUSED_RUN_WORKING_SAVE_COMMIT_ANCHOR_MISMATCH',
            'message': (
                f"paused run source commit_id '{effective_source_commit_id}' does not match current "
                f"Working Save commit anchor '{working_save_commit_anchor_id}'"
            ),
        })

    if effective_structure_fingerprint and current_structure_fingerprint != effective_structure_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_STRUCTURE_FINGERPRINT_MISMATCH',
            'message': (
                f"paused run structure_fingerprint '{effective_structure_fingerprint}' does not match current "
                f"Working Save structure_fingerprint '{current_structure_fingerprint}'"
            ),
        })

    if paused_execution_surface_fingerprint and resume_execution_surface_fingerprint and paused_execution_surface_fingerprint != resume_execution_surface_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_RESUME_REQUEST_EXECUTION_SURFACE_FINGERPRINT_MISMATCH',
            'message': (
                f"resume_request execution_surface_fingerprint '{resume_execution_surface_fingerprint}' does not match "
                f"paused_run_state execution_surface_fingerprint '{paused_execution_surface_fingerprint}'"
            ),
        })

    effective_execution_surface_fingerprint = paused_execution_surface_fingerprint or resume_execution_surface_fingerprint
    if effective_execution_surface_fingerprint and current_execution_surface_fingerprint != effective_execution_surface_fingerprint:
        issues.append({
            'code': 'PAUSED_RUN_EXECUTION_SURFACE_FINGERPRINT_MISMATCH',
            'message': (
                f"paused run execution_surface_fingerprint '{effective_execution_surface_fingerprint}' does not match current "
                f"Working Save execution_surface_fingerprint '{current_execution_surface_fingerprint}'"
            ),
        })

    if isinstance(pause_node_id, str) and pause_node_id and pause_node_id not in node_ids:
        issues.append({
            'code': 'PAUSED_RUN_ANCHOR_NODE_MISSING',
            'message': f"paused node '{pause_node_id}' is not present in current Working Save circuit",
        })

    if isinstance(resume_from_node_id, str) and resume_from_node_id and resume_from_node_id not in node_ids:
        issues.append({
            'code': 'PAUSED_RUN_RESUME_TARGET_MISSING',
            'message': f"resume target node '{resume_from_node_id}' is not present in current Working Save circuit",
        })

    completed_node_ids = paused_run_state.get('completed_node_ids')
    if isinstance(completed_node_ids, list):
        for node_id in completed_node_ids:
            if isinstance(node_id, str) and node_id and node_id not in node_ids:
                issues.append({
                    'code': 'PAUSED_RUN_COMPLETED_BOUNDARY_STALE',
                    'message': f"completed boundary node '{node_id}' is not present in current Working Save circuit",
                })

    anchor_valid = not issues
    stored_resume_ready = bool(last_run_summary.get('resume_ready', False))
    return {
        'checked': True,
        'source_commit_id': effective_source_commit_id,
        'structure_fingerprint': effective_structure_fingerprint,
        'working_save_structure_fingerprint': current_structure_fingerprint,
        'working_save_commit_anchor_id': working_save_commit_anchor_id,
        'execution_surface_fingerprint': effective_execution_surface_fingerprint,
        'working_save_execution_surface_fingerprint': current_execution_surface_fingerprint,
        'pause_node_id': pause_node_id,
        'resume_from_node_id': resume_from_node_id,
        'anchor_valid': anchor_valid,
        'issue_count': len(issues),
        'issues': issues,
        'effective_resume_ready': bool(stored_resume_ready and anchor_valid),
    }


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
    resume_anchor_validation = _validate_paused_run_resume_anchor(working_save, execution_record, last_run)
    if isinstance(resume_anchor_validation, dict):
        last_run['resume_anchor_validation'] = resume_anchor_validation
        last_run['resume_ready'] = bool(resume_anchor_validation.get('effective_resume_ready', False))
    prior_errors = list(working_save.runtime.errors)
    status = working_save.runtime.status
    if execution_record.meta.status in _SUCCESS_STATUSES:
        status = 'executed'
        errors: list[dict] = []
    elif execution_record.meta.status in _PAUSED_STATUSES:
        status = 'execution_paused'
        errors = []
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


def _has_execution_record_identity(record: dict) -> bool:
    if not isinstance(record, dict) or not record:
        return False
    meta = record.get('meta') if isinstance(record.get('meta'), dict) else {}
    source = record.get('source') if isinstance(record.get('source'), dict) else {}
    return bool(meta.get('run_id') and source.get('commit_id'))


def _looks_like_substantive_execution_record(record: dict) -> bool:
    if not _has_execution_record_identity(record):
        return False

    timeline = record.get('timeline') if isinstance(record.get('timeline'), dict) else {}
    outputs = record.get('outputs') if isinstance(record.get('outputs'), dict) else {}
    node_results = record.get('node_results') if isinstance(record.get('node_results'), dict) else {}

    primary_trace_ref = timeline.get('event_stream_ref') or timeline.get('trace_ref')
    if isinstance(primary_trace_ref, str) and primary_trace_ref:
        return True

    node_order = timeline.get('node_order')
    if isinstance(node_order, list) and any(isinstance(node_id, str) and node_id for node_id in node_order):
        return True

    final_outputs = outputs.get('final_outputs')
    if isinstance(final_outputs, list) and any(
        isinstance(item, dict) and isinstance(item.get('output_ref'), str) and item.get('output_ref')
        for item in final_outputs
    ):
        return True

    results = node_results.get('results')
    if isinstance(results, list) and any(
        isinstance(item, dict) and isinstance(item.get('node_id'), str) and item.get('node_id')
        for item in results
    ):
        return True

    return False


def _replay_payload_supplements_from_execution_record(execution_record: dict) -> dict:
    if not _looks_like_substantive_execution_record(execution_record):
        return {}

    timeline = execution_record.get('timeline') if isinstance(execution_record.get('timeline'), dict) else {}
    input_section = execution_record.get('input') if isinstance(execution_record.get('input'), dict) else {}
    outputs_section = execution_record.get('outputs') if isinstance(execution_record.get('outputs'), dict) else {}

    supplements: dict[str, object] = {}

    node_order = timeline.get('node_order')
    if isinstance(node_order, list) and node_order:
        normalized_node_order = [node_id for node_id in node_order if isinstance(node_id, str) and node_id]
        if normalized_node_order:
            supplements['node_order'] = normalized_node_order

    input_summary = input_section.get('input_summary')
    if isinstance(input_summary, dict) and input_summary:
        supplements['input_state'] = input_summary

    final_outputs = outputs_section.get('final_outputs')
    if isinstance(final_outputs, list) and final_outputs:
        expected_outputs: dict[str, object] = {}
        for item in final_outputs:
            if not isinstance(item, dict):
                continue
            output_ref = item.get('output_ref')
            if not isinstance(output_ref, str) or not output_ref:
                continue
            if 'value_payload' in item:
                expected_outputs[output_ref] = item.get('value_payload')
        if expected_outputs:
            supplements['expected_outputs'] = expected_outputs

    return supplements


def _merge_replay_payload_with_execution_record(replay_payload: dict, execution_record: dict) -> dict:
    merged = dict(replay_payload) if isinstance(replay_payload, dict) else {}
    supplements = _replay_payload_supplements_from_execution_record(execution_record)

    for key in ('node_order', 'input_state', 'expected_outputs'):
        if key in supplements:
            merged[key] = supplements[key]

    return merged


def create_serialized_execution_artifact_components(payload: dict) -> dict:
    """Normalize the shared execution-artifact component surface.

    This is the smallest shared transition-builder surface reused by run/export/replay.
    Prefer a substantive native execution_record when available; otherwise fall back to
    storage-side materialization from the payload when richer execution truth exists.
    When only a thin identity-bearing native execution_record exists, preserve its
    identity unless richer payload data allows a better reconstruction.
    """
    safe_payload = payload if isinstance(payload, dict) else {}
    native_execution_record = safe_payload.get('execution_record', {})
    has_substantive_native_execution_record = _looks_like_substantive_execution_record(native_execution_record)
    has_identity_native_execution_record = (
        isinstance(native_execution_record, dict)
        and isinstance(native_execution_record.get('meta'), dict)
        and isinstance(native_execution_record.get('source'), dict)
        and bool(native_execution_record['meta'].get('run_id'))
        and bool(native_execution_record['source'].get('commit_id'))
    )
    can_materialize_richer_truth = (
        isinstance(safe_payload.get('replay_payload'), dict)
        and isinstance(safe_payload['replay_payload'].get('expected_outputs'), dict)
        and bool(safe_payload['replay_payload'].get('expected_outputs'))
        and (
            bool((safe_payload.get('trace') if isinstance(safe_payload.get('trace'), dict) else {}))
            or bool((safe_payload['replay_payload'].get('node_order') if isinstance(safe_payload['replay_payload'].get('node_order'), list) else []))
            or bool(((safe_payload.get('result') if isinstance(safe_payload.get('result'), dict) else {}).get('node_results') if isinstance((safe_payload.get('result') if isinstance(safe_payload.get('result'), dict) else {}).get('node_results'), dict) else {}))
            or bool((safe_payload['replay_payload'].get('input_state') if isinstance(safe_payload['replay_payload'].get('input_state'), dict) else {}))
        )
    )
    if has_substantive_native_execution_record:
        execution_record = native_execution_record
    elif can_materialize_richer_truth:
        execution_record = materialize_execution_record_from_payload(safe_payload)
    elif has_identity_native_execution_record:
        execution_record = native_execution_record
    else:
        execution_record = materialize_execution_record_from_payload(safe_payload)

    reference_contract = build_execution_record_reference_contract_from_serialized_record(execution_record)

    replay_payload = safe_payload.get('replay_payload', {})
    if not isinstance(replay_payload, dict):
        replay_payload = {}

    source = execution_record.get('source', {}) if isinstance(execution_record, dict) else {}
    meta = execution_record.get('meta', {}) if isinstance(execution_record.get('meta'), dict) else {}
    run_id = meta.get('run_id')
    commit_id = source.get('commit_id')
    replay_payload = _merge_replay_payload_with_execution_record(replay_payload, execution_record)
    if run_id:
        replay_payload = dict(replay_payload)
        replay_payload['execution_id'] = run_id
    if commit_id:
        replay_payload = dict(replay_payload)
        replay_payload['commit_id'] = commit_id

    return {
        'run_id': run_id,
        'commit_id': commit_id,
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
