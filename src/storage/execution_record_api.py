from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.engine.execution_artifact_hashing import ExecutionHashReport, NodeOutputHash
from src.engine.execution_snapshot import ExecutionSnapshot, ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
from src.engine.paused_run_state import PausedRunState, PausedRunStateError
from src.engine.trace_intelligence import analyze_trace
from src.storage.models.execution_record_model import (
    ArtifactRecordCard,
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionIssue,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultCard,
    NodeResultsModel,
    NodeTimingCard,
    OutputResultCard,
)
from src.storage.serialization import save_execution_record_file, serialize_execution_record


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ms_to_iso(timestamp_ms: Optional[int]) -> Optional[str]:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).isoformat()


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    return repr(value)


def _summarize_value(value: Any) -> str:
    safe_value = _to_json_safe(value)
    text = str(safe_value)
    return text if len(text) <= 500 else text[:497] + '...'


def _semantic_status_from_run(status: str, has_outputs: bool) -> str:
    if status == 'completed':
        return 'normal' if has_outputs else 'failed'
    if status == 'paused':
        return 'paused'
    if status == 'partial':
        return 'partial'
    if status in {'failed', 'cancelled'}:
        return 'failed' if not has_outputs else 'partial'
    return 'normal' if has_outputs else 'failed'


def _trace_event_types(trace: dict[str, Any] | None) -> list[str]:
    events = trace.get('events') if isinstance(trace, dict) else None
    if not isinstance(events, list):
        return []
    result: list[str] = []
    for event in events:
        event_type = None
        if isinstance(event, str):
            event_type = event
        elif isinstance(event, dict):
            candidate = event.get('type')
            if isinstance(candidate, str):
                event_type = candidate
        if isinstance(event_type, str) and event_type:
            result.append(event_type)
    return result


def _infer_record_status(*, trace: dict[str, Any] | None = None, status: str | None = None) -> str:
    normalized_status = str(status).lower() if isinstance(status, str) and status else None
    event_types = {event_type.lower() for event_type in _trace_event_types(trace)}

    if 'execution_paused' in event_types or normalized_status == 'paused':
        return 'paused'
    if 'execution_failed' in event_types or normalized_status in {'failure', 'failed', 'error'}:
        return 'failed'
    if normalized_status in {'partial', 'cancelled'}:
        return normalized_status
    return 'completed'


def _termination_reason_from_trace(trace: dict[str, Any] | None, *, status: str) -> str | None:
    if status != 'paused' or not isinstance(trace, dict):
        return None
    events = trace.get('events')
    if not isinstance(events, list):
        return None
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        if str(event.get('type') or '').lower() != 'execution_paused':
            continue
        payload = event.get('payload')
        if isinstance(payload, dict):
            reason = payload.get('reason')
            if reason is not None:
                return str(reason)
    return None


def _pause_boundary_from_trace(trace: dict[str, Any] | None, *, status: str) -> dict[str, Any] | None:
    if status != 'paused' or not isinstance(trace, dict):
        return None
    events = trace.get('events')
    if not isinstance(events, list):
        return None
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        if str(event.get('type') or '').lower() != 'execution_paused':
            continue
        payload = event.get('payload')
        if not isinstance(payload, dict):
            return None
        resume = payload.get('resume') if isinstance(payload.get('resume'), dict) else {}
        boundary: dict[str, Any] = {
            'can_resume': bool(resume.get('can_resume', False)),
        }
        for field in ('pause_node_id', 'reason'):
            value = payload.get(field)
            if value is not None:
                boundary[field] = value
        for field in ('resume_from_node_id', 'resume_strategy', 'previous_execution_id'):
            value = resume.get(field)
            if value is not None:
                boundary[field] = value
        required_revalidation = resume.get('requires_revalidation')
        if isinstance(required_revalidation, list):
            boundary['requires_revalidation'] = [str(item) for item in required_revalidation if item is not None]
        return boundary
    return None


def _normalize_paused_run_state_payload(paused_run_state: Any) -> dict[str, Any] | None:
    if paused_run_state is None:
        return None
    if isinstance(paused_run_state, PausedRunState):
        return paused_run_state.to_dict()
    if isinstance(paused_run_state, dict):
        try:
            return PausedRunState.from_dict(paused_run_state).to_dict()
        except PausedRunStateError as exc:
            raise ValueError(f'invalid paused_run_state payload: {exc}') from exc
    raise TypeError('paused_run_state must be a PausedRunState or dict when provided')


def _resume_request_from_paused_run_state_payload(paused_run_state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(paused_run_state, dict) or not paused_run_state:
        return None
    try:
        return PausedRunState.from_dict(paused_run_state).to_resume_request_payload()
    except PausedRunStateError:
        return None




def _normalize_raw_artifact(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, '__dict__') and not isinstance(value, type):
        try:
            return dict(vars(value))
        except Exception:
            return value
    return value


def _extract_typed_artifact_envelope(artifact: Any) -> dict[str, Any] | None:
    artifact = _normalize_raw_artifact(artifact)
    if isinstance(artifact, dict):
        if all(key in artifact for key in ('artifact_id', 'artifact_type', 'producer_ref')):
            return artifact
        data = artifact.get('data')
        if isinstance(data, dict) and all(key in data for key in ('artifact_id', 'artifact_type', 'producer_ref')):
            return data
    return None


def _producer_node_from_producer_ref(producer_ref: Any) -> str | None:
    if not isinstance(producer_ref, str) or not producer_ref:
        return None
    if producer_ref.startswith('node.'):
        return producer_ref.split('.', 1)[1]
    return None


def _artifact_recorded_at(artifact: Any, envelope: dict[str, Any] | None = None) -> str | None:
    if isinstance(envelope, dict):
        created_at = envelope.get('created_at')
        if isinstance(created_at, str) and created_at:
            return created_at
    artifact = _normalize_raw_artifact(artifact)
    if isinstance(artifact, dict):
        created_at = artifact.get('created_at')
        if isinstance(created_at, str) and created_at:
            return created_at
        timestamp_ms = artifact.get('timestamp_ms')
        if isinstance(timestamp_ms, (int, float)):
            return _ms_to_iso(int(timestamp_ms))
    return None


def _typed_artifact_summary(payload: Any, artifact_type: str, metadata: dict[str, Any]) -> str:
    if artifact_type == 'validation_report' and isinstance(payload, dict):
        status = payload.get('aggregate_status') or metadata.get('aggregate_status')
        if isinstance(status, str) and status:
            return f'verification report ({status})'
    return _summarize_value(payload if payload is not None else {'artifact_type': artifact_type})


def _artifact_record_card_from_raw_artifact(artifact: Any, execution_id: str, index: int) -> ArtifactRecordCard:
    artifact = _normalize_raw_artifact(artifact)
    envelope = _extract_typed_artifact_envelope(artifact)

    if envelope is not None:
        outer_metadata = artifact.get('metadata') if isinstance(artifact, dict) and isinstance(artifact.get('metadata'), dict) else {}
        envelope_metadata = envelope.get('metadata') if isinstance(envelope.get('metadata'), dict) else {}
        merged_metadata = {**outer_metadata, **envelope_metadata}
        payload = envelope.get('payload')
        artifact_id = str(envelope.get('artifact_id') or f'artifact::typed::{index}')
        artifact_type = str(envelope.get('artifact_type') or 'json_object')
        producer_ref = str(envelope.get('producer_ref') or '') or None
        producer_node = None
        if isinstance(artifact, dict):
            outer_producer_node = artifact.get('producer_node')
            if isinstance(outer_producer_node, str) and outer_producer_node:
                producer_node = outer_producer_node
        if producer_node is None:
            producer_node = _producer_node_from_producer_ref(producer_ref)
        raw_trace_refs = envelope.get('trace_refs') if isinstance(envelope.get('trace_refs'), list) else []
        trace_refs = [str(item) for item in raw_trace_refs if item is not None]
        ref = None
        if isinstance(artifact, dict) and isinstance(artifact.get('ref'), str) and artifact.get('ref'):
            ref = artifact.get('ref')
        if ref is None:
            ref = f'artifact://{execution_id}/{artifact_id}'
        return ArtifactRecordCard(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            producer_node=producer_node,
            hash=(artifact.get('hash') if isinstance(artifact, dict) and isinstance(artifact.get('hash'), str) else None),
            ref=ref,
            summary=_typed_artifact_summary(payload, artifact_type, merged_metadata),
            artifact_schema_version=str(envelope.get('artifact_schema_version') or '') or None,
            producer_ref=producer_ref,
            validation_status=str(envelope.get('validation_status') or '') or None,
            validation_reason_codes=_collect_verifier_reason_codes(payload),
            recorded_at=_artifact_recorded_at(artifact, envelope),
            lineage_refs=[str(item) for item in envelope.get('lineage_refs', []) if item is not None] if isinstance(envelope.get('lineage_refs'), list) else [],
            trace_refs=trace_refs,
            metadata=_to_json_safe(merged_metadata) if merged_metadata else None,
            payload_preview=_to_json_safe(payload),
        )

    artifact_type = type(artifact).__name__
    artifact_ref = None
    summary_source = artifact
    producer_node = None
    if isinstance(artifact, dict):
        artifact_type = str(artifact.get('type') or artifact.get('artifact_type') or artifact_type)
        artifact_ref = artifact.get('ref') if isinstance(artifact.get('ref'), str) else None
        summary_source = artifact.get('summary') if artifact.get('summary') is not None else artifact
        producer_node = artifact.get('producer_node') if isinstance(artifact.get('producer_node'), str) else None
    return ArtifactRecordCard(
        artifact_id=f'artifact::raw::{index}',
        artifact_type=artifact_type,
        producer_node=producer_node,
        ref=artifact_ref or f'artifact://{execution_id}/raw/{index}',
        summary=_summarize_value(summary_source),
        recorded_at=_artifact_recorded_at(artifact),
        metadata=_to_json_safe(artifact) if isinstance(artifact, dict) else None,
        payload_preview=_to_json_safe(artifact) if isinstance(artifact, (dict, list)) else None,
    )


def _collect_verifier_reason_codes(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    codes: list[str] = []
    def _add(code: Any) -> None:
        if isinstance(code, str) and code and code not in codes:
            codes.append(code)
    for code in payload.get('blocking_reason_codes', []) if isinstance(payload.get('blocking_reason_codes'), list) else []:
        _add(code)
    for result in payload.get('constituent_results', []) if isinstance(payload.get('constituent_results'), list) else []:
        if not isinstance(result, dict):
            continue
        _add(result.get('reason_code'))
        for finding in result.get('findings', []) if isinstance(result.get('findings'), list) else []:
            if isinstance(finding, dict):
                _add(finding.get('reason_code'))
    return codes


def _build_verifier_summary(artifact_cards: list[ArtifactRecordCard]) -> dict[str, Any] | None:
    verifier_artifacts = [card for card in artifact_cards if card.artifact_type == 'validation_report']
    if not verifier_artifacts:
        typed_count = sum(1 for card in artifact_cards if card.artifact_schema_version)
        return {'typed_artifact_count': typed_count} if typed_count else None
    counts = {'pass': 0, 'warning': 0, 'fail': 0, 'inconclusive': 0}
    blocking_reason_codes: list[str] = []
    for card in verifier_artifacts:
        payload = card.payload_preview if isinstance(card.payload_preview, dict) else {}
        status = payload.get('aggregate_status') if isinstance(payload.get('aggregate_status'), str) else None
        if status in counts:
            counts[status] += 1
        for code in _collect_verifier_reason_codes(payload):
            if code not in blocking_reason_codes:
                blocking_reason_codes.append(code)
    return {
        'verifier_report_count': len(verifier_artifacts),
        'typed_artifact_count': sum(1 for card in artifact_cards if card.artifact_schema_version),
        'status_counts': counts,
        'blocking_reason_codes': blocking_reason_codes,
    }

def _artifact_id_for_node(node_id: str) -> str:
    return f'artifact::{node_id}'


def _node_trace_ref(trace_ref: str | None, event_stream_ref: str | None, node_id: str) -> str | None:
    if event_stream_ref:
        return f'{event_stream_ref}#node:{node_id}'
    if trace_ref:
        return f'{trace_ref}#node:{node_id}'
    return None


def _build_timing_card(span: NodeExecutionSpan) -> NodeTimingCard:
    return NodeTimingCard(
        node_id=span.node_id,
        started_at=_ms_to_iso(span.start_ms),
        finished_at=_ms_to_iso(span.end_ms),
        duration_ms=span.duration_ms,
        outcome=span.status if span.status in {"success", "failed", "skipped", "partial", "cancelled"} else "success",
    )


def _build_artifact_cards(
    snapshot: ExecutionSnapshot,
    explicit_artifact_refs: Iterable[ArtifactRecordCard] | None,
    output_cards: list[OutputResultCard],
) -> list[ArtifactRecordCard]:
    artifact_cards = list(explicit_artifact_refs or [])
    existing_ids = {card.artifact_id for card in artifact_cards}
    for node_hash in snapshot.node_hashes:
        artifact_id = _artifact_id_for_node(node_hash.node_id)
        if artifact_id in existing_ids:
            continue
        artifact_cards.append(
            ArtifactRecordCard(
                artifact_id=artifact_id,
                artifact_type='node_output_hash',
                producer_node=node_hash.node_id,
                hash=node_hash.hash_value,
                ref=f'hash://{node_hash.algorithm}/{node_hash.hash_value}',
                summary=f'Output hash for node {node_hash.node_id}',
            )
        )
        existing_ids.add(artifact_id)
    for output_card in output_cards:
        artifact_id = f'artifact::output::{output_card.output_ref}'
        if artifact_id in existing_ids:
            continue
        artifact_cards.append(
            ArtifactRecordCard(
                artifact_id=artifact_id,
                artifact_type='final_output',
                ref=output_card.value_ref or f'output://{snapshot.execution_id}/{output_card.output_ref}',
                summary=f'Final output artifact for {output_card.output_ref}',
            )
        )
        existing_ids.add(artifact_id)
    return artifact_cards


def _normalize_precision_summary(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return _to_json_safe(payload)
    return None


def _extract_trace_intelligence_summary(
    trace: dict[str, Any] | None,
    *,
    run_ref: str,
    trace_refs: list[str] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    node_results = trace.get('node_results') if isinstance(trace.get('node_results'), dict) else {}
    node_events: list[dict[str, Any]] = []
    for node_id, node_result in node_results.items():
        if not isinstance(node_id, str) or not isinstance(node_result, dict):
            continue
        nested_trace = node_result.get('trace') if isinstance(node_result.get('trace'), dict) else {}
        timings = nested_trace.get('timings_ms') if isinstance(nested_trace.get('timings_ms'), dict) else {}
        total_duration = 0.0
        for value in timings.values():
            if isinstance(value, (int, float)):
                total_duration += float(value)
        duration_ms = total_duration if total_duration > 0 else None
        precision = nested_trace.get('precision') if isinstance(nested_trace.get('precision'), dict) else {}
        routing_entries = precision.get('routing') if isinstance(precision.get('routing'), list) else []
        latest_route = routing_entries[-1] if routing_entries else {}
        route_decision = latest_route.get('route_decision') if isinstance(latest_route, dict) else {}
        raw_status = str(node_result.get('status') or ('error' if node_result.get('error') is not None else 'success')).lower()
        normalized_status = 'error' if raw_status in {'failed', 'error'} else raw_status
        reason_code = None
        error_payload = node_result.get('error')
        if isinstance(error_payload, dict):
            reason_code = error_payload.get('type') or error_payload.get('reason_code') or error_payload.get('message')
        elif error_payload is not None:
            reason_code = str(error_payload)
        verifier_trace = nested_trace.get('verifier_trace') if isinstance(nested_trace.get('verifier_trace'), list) else []
        if reason_code is None and verifier_trace:
            latest_verifier = verifier_trace[-1] if isinstance(verifier_trace[-1], dict) else {}
            blocking_codes = latest_verifier.get('blocking_reason_codes') if isinstance(latest_verifier.get('blocking_reason_codes'), list) else []
            if blocking_codes:
                reason_code = blocking_codes[0]
        node_events.append({
            'node_id': node_id,
            'status': normalized_status,
            'reason_code': reason_code,
            'failure_category': 'runtime_error' if normalized_status == 'error' else None,
            'duration_ms': duration_ms,
            'cost_estimate': route_decision.get('estimated_cost') if isinstance(route_decision, dict) else None,
        })
    if not node_events:
        return None
    report = analyze_trace(run_ref=run_ref, node_events=node_events, trace_refs=trace_refs)
    return report.to_dict()


def _extract_branch_summary(trace: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    events = trace.get('events') if isinstance(trace.get('events'), list) else []
    branch_events: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get('type') or '').lower() != 'branch_candidate_declared':
            continue
        payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
        branch_events.append(payload)
    if not branch_events:
        return None

    branch_ids: list[str] = []
    target_refs: list[str] = []
    policies: list[str] = []
    recommended_next_steps: list[str] = []
    aggregate_statuses: list[str] = []
    reason_codes: list[str] = []
    for payload in branch_events:
        branch_ref = payload.get('branch_ref') if isinstance(payload.get('branch_ref'), dict) else {}
        branch_id = branch_ref.get('branch_id')
        branch_policy = branch_ref.get('branch_policy')
        target_ref = payload.get('target_ref')
        recommended_next_step = payload.get('recommended_next_step')
        aggregate_status = payload.get('aggregate_status')
        for code in payload.get('blocking_reason_codes', []) if isinstance(payload.get('blocking_reason_codes'), list) else []:
            if isinstance(code, str) and code and code not in reason_codes:
                reason_codes.append(code)
        if isinstance(branch_id, str) and branch_id and branch_id not in branch_ids:
            branch_ids.append(branch_id)
        if isinstance(branch_policy, str) and branch_policy and branch_policy not in policies:
            policies.append(branch_policy)
        if isinstance(target_ref, str) and target_ref and target_ref not in target_refs:
            target_refs.append(target_ref)
        if isinstance(recommended_next_step, str) and recommended_next_step and recommended_next_step not in recommended_next_steps:
            recommended_next_steps.append(recommended_next_step)
        if isinstance(aggregate_status, str) and aggregate_status and aggregate_status not in aggregate_statuses:
            aggregate_statuses.append(aggregate_status)

    return {
        'branch_candidate_count': len(branch_events),
        'branch_ids': branch_ids,
        'policies': policies,
        'target_refs': target_refs,
        'recommended_next_steps': recommended_next_steps,
        'aggregate_statuses': aggregate_statuses,
        'reason_codes': reason_codes,
    }


def _extract_human_decision_summary(trace: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    events = trace.get('events') if isinstance(trace.get('events'), list) else []
    decision_events: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if str(event.get('type') or '').lower() != 'human_decision_recorded':
            continue
        payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
        decision_events.append(payload)
    if not decision_events:
        return None

    decision_types: list[str] = []
    actor_refs: list[str] = []
    downstream_actions: list[str] = []
    target_refs: list[str] = []
    for payload in decision_events:
        decision_type = payload.get('decision_type')
        actor_ref = payload.get('actor_ref')
        downstream_action = payload.get('downstream_action')
        target_ref = payload.get('target_ref')
        if isinstance(decision_type, str) and decision_type and decision_type not in decision_types:
            decision_types.append(decision_type)
        if isinstance(actor_ref, str) and actor_ref and actor_ref not in actor_refs:
            actor_refs.append(actor_ref)
        if isinstance(downstream_action, str) and downstream_action and downstream_action not in downstream_actions:
            downstream_actions.append(downstream_action)
        if isinstance(target_ref, str) and target_ref and target_ref not in target_refs:
            target_refs.append(target_ref)

    return {
        'decision_count': len(decision_events),
        'decision_types': decision_types,
        'actor_refs': actor_refs,
        'downstream_actions': downstream_actions,
        'target_refs': target_refs,
    }


def _extract_precision_from_trace(trace: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, dict[str, Any]]]:
    if not isinstance(trace, dict):
        return None, None, None, {}

    routing_entries = trace.get('routing') if isinstance(trace.get('routing'), list) else []
    safety_entries = trace.get('safety_gates') if isinstance(trace.get('safety_gates'), list) else []
    confidence_entries = trace.get('confidence_assessments') if isinstance(trace.get('confidence_assessments'), list) else []

    node_precision: dict[str, dict[str, Any]] = {}
    node_results = trace.get('node_results') if isinstance(trace.get('node_results'), dict) else {}
    for node_id, node_result in node_results.items():
        if not isinstance(node_id, str):
            continue
        precision_payload = None
        if isinstance(node_result, dict):
            precision_payload = node_result.get('precision')
            if precision_payload is None:
                nested_trace = node_result.get('trace') if isinstance(node_result.get('trace'), dict) else {}
                precision_payload = nested_trace.get('precision')
        else:
            precision_payload = getattr(node_result, 'precision', None)
            if precision_payload is None:
                node_trace = getattr(node_result, 'trace', None)
                precision_payload = getattr(node_trace, 'precision', None)
        if isinstance(precision_payload, dict):
            node_precision[node_id] = _to_json_safe(precision_payload)
            routing = precision_payload.get('routing') if isinstance(precision_payload.get('routing'), list) else []
            safety = precision_payload.get('safety_gates') if isinstance(precision_payload.get('safety_gates'), list) else []
            confidence = precision_payload.get('confidence_assessments') if isinstance(precision_payload.get('confidence_assessments'), list) else []
            routing_entries.extend([item for item in routing if isinstance(item, dict)])
            safety_entries.extend([item for item in safety if isinstance(item, dict)])
            confidence_entries.extend([item for item in confidence if isinstance(item, dict)])
            node_confidence = precision_payload.get('node_confidence')
            if isinstance(node_confidence, dict):
                confidence_entries.append(node_confidence)

    routing_summary = None
    if routing_entries:
        last_route = routing_entries[-1]
        route_tiers = [item.get('route_decision', {}).get('selected_route_tier') for item in routing_entries if isinstance(item.get('route_decision'), dict)]
        routing_summary = {
            'route_count': len(routing_entries),
            'last_selected_provider_id': ((last_route.get('route_decision') or {}).get('selected_provider_id') if isinstance(last_route.get('route_decision'), dict) else None),
            'route_tiers': [tier for tier in route_tiers if isinstance(tier, str)],
        }

    safety_summary = None
    if safety_entries:
        statuses = [item.get('status') for item in safety_entries if isinstance(item.get('status'), str)]
        safety_summary = {
            'gate_count': len(safety_entries),
            'statuses': statuses,
            'blocked': any(status == 'block' for status in statuses),
        }

    confidence_summary = None
    if confidence_entries:
        scores = [float(item.get('confidence_score')) for item in confidence_entries if isinstance(item, dict) and item.get('confidence_score') is not None]
        node_confidences = [item for item in confidence_entries if isinstance(item, dict) and isinstance(item.get('target_ref'), str) and item.get('target_ref', '').endswith('.output')]
        confidence_summary = {
            'assessment_count': len(confidence_entries),
            'node_confidence_count': len(node_confidences),
            'max_confidence_score': max(scores) if scores else None,
            'min_confidence_score': min(scores) if scores else None,
        }

    return routing_summary, safety_summary, confidence_summary, node_precision


def _build_node_result_cards(
    snapshot: ExecutionSnapshot,
    *,
    trace_ref: str | None,
    event_stream_ref: str | None,
    artifact_ids_by_node: dict[str, list[str]],
    artifact_cards_by_node: dict[str, list[ArtifactRecordCard]],
    node_precision: dict[str, dict[str, Any]] | None = None,
) -> list[NodeResultCard]:
    hash_map = {item.node_id: item for item in snapshot.node_hashes}
    cards: list[NodeResultCard] = []
    for span in snapshot.timeline.node_spans:
        output = snapshot.node_outputs.get(span.node_id)
        summary = None if output is None else _summarize_value(output)
        output_type = None if output is None else type(output).__name__
        output_preview = None if output is None else _to_json_safe(output)
        metrics = None
        node_hash = hash_map.get(span.node_id)
        if node_hash is not None:
            metrics = {'output_hash': node_hash.hash_value, 'hash_algorithm': node_hash.algorithm}
        artifact_refs = list(artifact_ids_by_node.get(span.node_id, []))
        node_artifact_cards = list(artifact_cards_by_node.get(span.node_id, []))
        typed_artifact_refs = [card.artifact_id for card in node_artifact_cards if card.artifact_schema_version]
        verifier_cards = [card for card in node_artifact_cards if card.artifact_type == 'validation_report' and isinstance(card.payload_preview, dict)]
        verifier_status = None
        verifier_reason_codes: list[str] = []
        if verifier_cards:
            first_payload = verifier_cards[0].payload_preview if isinstance(verifier_cards[0].payload_preview, dict) else {}
            verifier_status = first_payload.get('aggregate_status') if isinstance(first_payload.get('aggregate_status'), str) else None
            for card in verifier_cards:
                for code in _collect_verifier_reason_codes(card.payload_preview):
                    if code not in verifier_reason_codes:
                        verifier_reason_codes.append(code)
        precision_payload = (node_precision or {}).get(span.node_id, {})
        route_entries = precision_payload.get('routing') if isinstance(precision_payload.get('routing'), list) else []
        safety_entries = precision_payload.get('safety_gates') if isinstance(precision_payload.get('safety_gates'), list) else []
        confidence_entries = precision_payload.get('confidence_assessments') if isinstance(precision_payload.get('confidence_assessments'), list) else []
        cards.append(
            NodeResultCard(
                node_id=span.node_id,
                status=span.status if span.status in {"success", "failed", "skipped", "partial", "cancelled"} else "success",
                output_summary=summary,
                output_type=output_type,
                output_preview=output_preview,
                artifact_refs=artifact_refs,
                typed_artifact_refs=typed_artifact_refs,
                verifier_status=verifier_status,
                verifier_reason_codes=verifier_reason_codes,
                warning_count=sum(1 for card in verifier_cards if isinstance(card.payload_preview, dict) and card.payload_preview.get('aggregate_status') == 'warning'),
                error_count=(1 if span.status == 'failed' else 0) + sum(1 for card in verifier_cards if isinstance(card.payload_preview, dict) and card.payload_preview.get('aggregate_status') == 'fail'),
                trace_ref=_node_trace_ref(trace_ref, event_stream_ref, span.node_id),
                metrics=metrics,
                route_summary=_normalize_precision_summary(route_entries[-1]) if route_entries else None,
                safety_summary=_normalize_precision_summary(safety_entries[-1]) if safety_entries else None,
                confidence_summary=_normalize_precision_summary(precision_payload.get('node_confidence') or (confidence_entries[-1] if confidence_entries else None)),
            )
        )
    return cards


def _build_output_cards(final_outputs: dict[str, Any] | None, *, trace_ref: str | None) -> list[OutputResultCard]:
    cards: list[OutputResultCard] = []
    for output_ref, value in (final_outputs or {}).items():
        cards.append(
            OutputResultCard(
                output_ref=output_ref,
                value_summary=_summarize_value(value),
                value_payload=_to_json_safe(value),
                value_type=type(value).__name__,
                value_ref=f'{trace_ref}#output:{output_ref}' if trace_ref else None,
            )
        )
    return cards


def _build_observability_metrics(snapshot: ExecutionSnapshot) -> dict[str, Any]:
    return {
        'execution_id': snapshot.execution_id,
        'duration_ms': snapshot.timeline.duration_ms,
        'node_count': len(snapshot.timeline.node_spans),
        'hashed_nodes': len(snapshot.node_hashes),
    }


def _merge_observability_refs(
    provided_refs: list[str] | None,
    *,
    trace_ref: str | None,
    event_stream_ref: str | None,
    artifact_cards: list[ArtifactRecordCard],
) -> list[str] | None:
    refs: list[str] = []
    for item in provided_refs or []:
        if item not in refs:
            refs.append(item)
    for item in [trace_ref, event_stream_ref]:
        if item and item not in refs:
            refs.append(item)
    for card in artifact_cards:
        if card.ref and card.ref not in refs:
            refs.append(card.ref)
        for trace_ref_item in card.trace_refs:
            if trace_ref_item and trace_ref_item not in refs:
                refs.append(trace_ref_item)
    return refs or None


def create_execution_record_from_snapshot(
    snapshot: ExecutionSnapshot,
    *,
    commit_id: str,
    trigger_type: str = 'manual_run',
    working_save_id: str | None = None,
    trigger_reason: str | None = None,
    status: str = 'completed',
    title: str | None = None,
    description: str | None = None,
    created_at: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    input_summary: dict[str, Any] | None = None,
    input_ref: str | None = None,
    input_hash: str | None = None,
    schema_summary: str | None = None,
    trace_ref: str | None = None,
    event_stream_ref: str | None = None,
    final_outputs: dict[str, Any] | None = None,
    artifact_refs: Iterable[ArtifactRecordCard] | None = None,
    warnings: Iterable[ExecutionIssue] | None = None,
    errors: Iterable[ExecutionIssue] | None = None,
    failure_point: str | None = None,
    termination_reason: str | None = None,
    pause_boundary: dict[str, Any] | None = None,
    paused_run_state: Any = None,
    provider_usage_summary: dict[str, Any] | None = None,
    plugin_usage_summary: dict[str, Any] | None = None,
    trace_summary: str | None = None,
    observability_refs: list[str] | None = None,
    routing_summary: dict[str, Any] | None = None,
    safety_summary: dict[str, Any] | None = None,
    confidence_summary: dict[str, Any] | None = None,
    node_precision: dict[str, dict[str, Any]] | None = None,
    trace_intelligence_summary: dict[str, Any] | None = None,
    human_decision_summary: dict[str, Any] | None = None,
    branch_summary: dict[str, Any] | None = None,
) -> ExecutionRecordModel:
    created = created_at or _iso_now()
    started = started_at or _ms_to_iso(snapshot.timeline.start_ms) or created
    finished = finished_at or _ms_to_iso(snapshot.timeline.end_ms)
    timing_cards = [_build_timing_card(span) for span in snapshot.timeline.node_spans]
    node_order = [span.node_id for span in snapshot.timeline.node_spans]
    output_cards = _build_output_cards(final_outputs if final_outputs is not None else snapshot.node_outputs, trace_ref=trace_ref)
    artifact_card_list = _build_artifact_cards(snapshot, artifact_refs, output_cards)
    artifact_ids_by_node: dict[str, list[str]] = {}
    artifact_cards_by_node: dict[str, list[ArtifactRecordCard]] = {}
    for card in artifact_card_list:
        if not card.producer_node:
            continue
        artifact_ids_by_node.setdefault(card.producer_node, []).append(card.artifact_id)
        artifact_cards_by_node.setdefault(card.producer_node, []).append(card)
    node_result_cards = _build_node_result_cards(
        snapshot,
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        artifact_ids_by_node=artifact_ids_by_node,
        artifact_cards_by_node=artifact_cards_by_node,
        node_precision=node_precision,
    )
    trace_summary_value = trace_summary or f'Execution {snapshot.execution_id} observed {len(snapshot.timeline.node_spans)} node span(s).'
    if isinstance(trace_intelligence_summary, dict) and trace_intelligence_summary.get('explanation'):
        trace_summary_value = f"{trace_summary_value} {trace_intelligence_summary['explanation']}"
    resolved_observability_refs = _merge_observability_refs(
        observability_refs,
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        artifact_cards=artifact_card_list,
    )
    normalized_paused_run_state = _normalize_paused_run_state_payload(paused_run_state)
    if normalized_paused_run_state is not None and commit_id and not normalized_paused_run_state.get('source_commit_id'):
        normalized_paused_run_state = dict(normalized_paused_run_state)
        normalized_paused_run_state['source_commit_id'] = commit_id
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id=snapshot.execution_id,
            record_format_version='1.0.0',
            created_at=created,
            started_at=started,
            finished_at=finished,
            status=status,
            title=title,
            description=description,
        ),
        source=ExecutionSourceModel(
            commit_id=commit_id,
            working_save_id=working_save_id,
            trigger_type=trigger_type,
            trigger_reason=trigger_reason,
        ),
        input=ExecutionInputModel(
            input_summary=input_summary,
            input_ref=input_ref,
            input_hash=input_hash,
            schema_summary=schema_summary,
        ),
        timeline=ExecutionTimelineModel(
            total_duration_ms=snapshot.timeline.duration_ms,
            event_count=len(snapshot.timeline.node_spans),
            node_order=node_order,
            started_nodes=timing_cards,
            completed_nodes=timing_cards,
            trace_ref=trace_ref,
            event_stream_ref=event_stream_ref,
        ),
        node_results=NodeResultsModel(results=node_result_cards),
        outputs=ExecutionOutputModel(
            final_outputs=output_cards,
            output_summary=f'{len(output_cards)} output(s) recorded' if output_cards else 'No final outputs recorded',
            semantic_status=_semantic_status_from_run(status, bool(output_cards)),
        ),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=artifact_card_list,
            artifact_count=len(artifact_card_list),
            artifact_summary=f'{len(artifact_card_list)} artifact ref(s) recorded' if artifact_card_list else 'No artifact refs recorded',
        ),
        diagnostics=ExecutionDiagnosticsModel(
            warnings=list(warnings or []),
            errors=list(errors or []),
            failure_point=failure_point,
            termination_reason=termination_reason,
            pause_boundary=_to_json_safe(pause_boundary) if pause_boundary is not None else None,
            paused_run_state=normalized_paused_run_state,
        ),
        observability=ExecutionObservabilityModel(
            metrics=_build_observability_metrics(snapshot),
            provider_usage_summary=provider_usage_summary,
            plugin_usage_summary=plugin_usage_summary,
            verifier_summary=_build_verifier_summary(artifact_card_list),
            trace_summary=trace_summary_value,
            observability_refs=resolved_observability_refs,
            routing_summary=_normalize_precision_summary(routing_summary),
            safety_summary=_normalize_precision_summary(safety_summary),
            confidence_summary=_normalize_precision_summary(confidence_summary),
            trace_intelligence_summary=_to_json_safe(trace_intelligence_summary) if trace_intelligence_summary is not None else None,
            human_decision_summary=_to_json_safe(human_decision_summary) if human_decision_summary is not None else None,
            branch_summary=_to_json_safe(branch_summary) if branch_summary is not None else None,
        ),
    )




def build_execution_record_reference_contract_from_serialized_record(record_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record_payload, dict):
        return {}

    timeline = record_payload.get('timeline') if isinstance(record_payload.get('timeline'), dict) else {}
    outputs = record_payload.get('outputs') if isinstance(record_payload.get('outputs'), dict) else {}
    artifacts = record_payload.get('artifacts') if isinstance(record_payload.get('artifacts'), dict) else {}
    observability = record_payload.get('observability') if isinstance(record_payload.get('observability'), dict) else {}
    source = record_payload.get('source') if isinstance(record_payload.get('source'), dict) else {}
    meta = record_payload.get('meta') if isinstance(record_payload.get('meta'), dict) else {}

    primary_trace_ref = timeline.get('event_stream_ref') or timeline.get('trace_ref')

    node_trace_refs = {}
    node_results = record_payload.get('node_results') if isinstance(record_payload.get('node_results'), dict) else {}
    for item in node_results.get('results', []) if isinstance(node_results.get('results'), list) else []:
        if isinstance(item, dict) and item.get('node_id') and item.get('trace_ref'):
            node_trace_refs[str(item['node_id'])] = item['trace_ref']

    output_value_refs = {}
    unresolved_output_refs = []
    for item in outputs.get('final_outputs', []) if isinstance(outputs.get('final_outputs'), list) else []:
        if not isinstance(item, dict) or not item.get('output_ref'):
            continue
        output_ref = str(item['output_ref'])
        value_ref = item.get('value_ref')
        if value_ref:
            output_value_refs[output_ref] = value_ref
        else:
            unresolved_output_refs.append(output_ref)

    artifact_refs = {}
    unresolved_artifact_refs = []
    for item in artifacts.get('artifact_refs', []) if isinstance(artifacts.get('artifact_refs'), list) else []:
        if not isinstance(item, dict) or not item.get('artifact_id'):
            continue
        artifact_id = str(item['artifact_id'])
        ref = item.get('ref')
        if ref:
            artifact_refs[artifact_id] = ref
        else:
            unresolved_artifact_refs.append(artifact_id)

    observability_refs = list(observability.get('observability_refs') or []) if isinstance(observability.get('observability_refs'), list) else []
    diagnostics = record_payload.get('diagnostics') if isinstance(record_payload.get('diagnostics'), dict) else {}
    pause_boundary = diagnostics.get('pause_boundary') if isinstance(diagnostics.get('pause_boundary'), dict) else {}
    paused_run_state = diagnostics.get('paused_run_state') if isinstance(diagnostics.get('paused_run_state'), dict) else {}
    resume_request = _resume_request_from_paused_run_state_payload(paused_run_state)
    trigger_type = source.get('trigger_type') if isinstance(source.get('trigger_type'), str) else 'manual_run'
    is_replay_run = trigger_type == 'replay_run'
    return {
        'run_id': meta.get('run_id'),
        'commit_id': source.get('commit_id'),
        'trigger_type': trigger_type,
        'is_replay_run': is_replay_run,
        'primary_trace_ref': primary_trace_ref,
        'trace_ref': timeline.get('trace_ref'),
        'event_stream_ref': timeline.get('event_stream_ref'),
        'node_trace_refs': node_trace_refs,
        'output_value_refs': output_value_refs,
        'artifact_refs': artifact_refs,
        'unresolved_output_refs': unresolved_output_refs,
        'unresolved_artifact_refs': unresolved_artifact_refs,
        'observability_refs': observability_refs,
        'termination_reason': diagnostics.get('termination_reason'),
        'pause_boundary': dict(pause_boundary) if pause_boundary else None,
        'paused_run_state': dict(paused_run_state) if paused_run_state else None,
        'resume_request': dict(resume_request) if resume_request else None,
        'is_replay_ready': bool(primary_trace_ref and not unresolved_output_refs),
        'is_audit_ready': bool(primary_trace_ref and not unresolved_artifact_refs),
        'is_resume_ready': bool(not is_replay_run and ((pause_boundary.get('can_resume')) or resume_request)),
    }


def _status_from_payload_node_result(node_data: Any) -> str:
    if not isinstance(node_data, dict):
        return 'success'
    status = str(node_data.get('status') or 'success').lower()
    if status in {'success', 'completed', 'ok'}:
        return 'success'
    if status in {'failure', 'failed', 'error'}:
        return 'failed'
    if status in {'skipped', 'partial', 'cancelled'}:
        return status
    return 'success'


def _build_snapshot_from_payload(payload: dict[str, Any]) -> ExecutionSnapshot | None:
    replay_payload = payload.get('replay_payload') if isinstance(payload.get('replay_payload'), dict) else {}
    if not replay_payload:
        return None

    execution_id = str(replay_payload.get('execution_id') or payload.get('run_id') or 'unknown-execution')
    node_order = replay_payload.get('node_order') if isinstance(replay_payload.get('node_order'), list) else []
    result = payload.get('result') if isinstance(payload.get('result'), dict) else {}
    result_node_results = result.get('node_results') if isinstance(result.get('node_results'), dict) else {}
    expected_outputs = replay_payload.get('expected_outputs') if isinstance(replay_payload.get('expected_outputs'), dict) else {}

    node_outputs: dict[str, Any] = {}
    spans: list[NodeExecutionSpan] = []
    start_ms = 0
    for index, node_id in enumerate([n for n in node_order if isinstance(n, str)]):
        node_data = result_node_results.get(node_id)
        if isinstance(node_data, dict) and 'output' in node_data:
            node_outputs[node_id] = node_data.get('output')
        elif node_id in expected_outputs:
            node_outputs[node_id] = expected_outputs.get(node_id)
        elif node_id in result.get('state', {}):
            node_outputs[node_id] = result['state'].get(node_id)
        else:
            node_outputs[node_id] = None
        status = _status_from_payload_node_result(node_data)
        spans.append(NodeExecutionSpan(node_id=node_id, start_ms=index, end_ms=index + 1, duration_ms=1, status=status))
    if not spans and expected_outputs:
        for index, (node_id, value) in enumerate(expected_outputs.items()):
            if not isinstance(node_id, str):
                continue
            node_outputs[node_id] = value
            spans.append(NodeExecutionSpan(node_id=node_id, start_ms=index, end_ms=index + 1, duration_ms=1, status='success'))

    if not spans and not node_outputs:
        return None

    timeline = ExecutionTimeline(
        execution_id=execution_id,
        start_ms=start_ms,
        end_ms=len(spans),
        duration_ms=len(spans),
        node_spans=spans,
    )
    hash_report = ExecutionHashReport(execution_id=execution_id, node_hashes=[])
    return ExecutionSnapshotBuilder().build(
        execution_id=execution_id,
        timeline=timeline,
        outputs=node_outputs,
        hash_report=hash_report,
    )


def _artifact_record_cards_from_raw_artifacts(artifacts: list[Any] | None, execution_id: str) -> list[ArtifactRecordCard]:
    cards: list[ArtifactRecordCard] = []
    for index, artifact in enumerate(artifacts or [], start=1):
        cards.append(_artifact_record_card_from_raw_artifact(artifact, execution_id, index))
    return cards




def create_serialized_execution_record_from_circuit_run(
    circuit: dict[str, Any],
    final_state: dict[str, Any],
    *,
    started_at: float | None = None,
    ended_at: float | None = None,
    execution_id: str | None = None,
    input_state: dict[str, Any] | None = None,
    trace: dict[str, Any] | None = None,
    artifacts: list[Any] | None = None,
    commit_id: str | None = None,
    paused_run_state: Any = None,
) -> dict[str, Any]:
    if not isinstance(circuit, dict):
        return {}

    circuit_nodes = circuit.get('nodes') if isinstance(circuit.get('nodes'), list) else []
    node_order = [node.get('id') for node in circuit_nodes if isinstance(node, dict) and isinstance(node.get('id'), str)]
    resolved_execution_id = str(execution_id or circuit.get('id') or 'unknown-execution')

    spans: list[NodeExecutionSpan] = []
    outputs: dict[str, Any] = {}
    hash_nodes: list[NodeOutputHash] = []
    for index, node_id in enumerate(node_order):
        output = final_state.get(node_id) if isinstance(final_state, dict) else None
        outputs[node_id] = output
        spans.append(NodeExecutionSpan(node_id=node_id, start_ms=index, end_ms=index + 1, duration_ms=1, status='success'))
        if output is not None:
            safe_output = _to_json_safe(output)
            hash_nodes.append(NodeOutputHash(node_id=node_id, algorithm='repr', hash_value=str(abs(hash(repr(safe_output))))))

    timeline = ExecutionTimeline(
        execution_id=resolved_execution_id,
        start_ms=0,
        end_ms=len(spans),
        duration_ms=len(spans),
        node_spans=spans,
    )
    hash_report = ExecutionHashReport(execution_id=resolved_execution_id, node_hashes=hash_nodes)
    snapshot = ExecutionSnapshotBuilder().build(
        execution_id=resolved_execution_id,
        timeline=timeline,
        outputs=outputs,
        hash_report=hash_report,
    )

    trace_ref = f'trace://{resolved_execution_id}' if isinstance(trace, dict) and trace else None
    event_stream_ref = f'events://{resolved_execution_id}' if isinstance(trace, dict) and trace.get('events') else None
    explicit_artifact_refs = _artifact_record_cards_from_raw_artifacts(artifacts, resolved_execution_id)
    routing_summary, safety_summary, confidence_summary, node_precision = _extract_precision_from_trace(trace)
    trace_refs = [item for item in [trace_ref, event_stream_ref] if item]
    trace_intelligence_summary = _extract_trace_intelligence_summary(trace, run_ref=resolved_execution_id, trace_refs=trace_refs)
    human_decision_summary = _extract_human_decision_summary(trace)
    branch_summary = _extract_branch_summary(trace)

    resolved_paused_run_state = paused_run_state
    if resolved_paused_run_state is None:
        resolved_paused_run_state = getattr(final_state, 'paused_run_state', None)

    created_at = _iso_now()
    started_iso = None
    finished_iso = None
    if started_at is not None:
        started_iso = datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat()
    if ended_at is not None:
        finished_iso = datetime.fromtimestamp(ended_at, tz=timezone.utc).isoformat()

    record_status = _infer_record_status(trace=trace)
    record = create_execution_record_from_snapshot(
        snapshot,
        commit_id=str(commit_id or f'uncommitted::{resolved_execution_id}'),
        trigger_type='manual_run',
        trigger_reason='circuit_run_materialization',
        status=record_status,
        title=str(circuit.get('id') or 'circuit-run'),
        input_summary=input_state or {},
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        final_outputs=outputs,
        artifact_refs=explicit_artifact_refs,
        provider_usage_summary={'circuit_id': circuit.get('id')},
        trace_summary=f'Circuit run materialized for {resolved_execution_id} with {len(node_order)} node(s).',
        termination_reason=_termination_reason_from_trace(trace, status=record_status),
        pause_boundary=_pause_boundary_from_trace(trace, status=record_status),
        paused_run_state=resolved_paused_run_state,
        observability_refs=trace_refs,
        routing_summary=routing_summary,
        safety_summary=safety_summary,
        confidence_summary=confidence_summary,
        node_precision=node_precision,
        trace_intelligence_summary=trace_intelligence_summary,
        human_decision_summary=human_decision_summary,
        branch_summary=branch_summary,
    )
    return serialize_execution_record(record)
def create_serialized_execution_record_from_savefile_trace(
    savefile: Any,
    trace: Any,
    *,
    started_at: float | None = None,
    ended_at: float | None = None,
    commit_id: str | None = None,
    working_save_id: str | None = None,
) -> dict[str, Any]:
    if savefile is None or trace is None:
        return {}

    run_id = str(getattr(trace, 'run_id', None) or 'unknown-execution')
    node_results = getattr(trace, 'node_results', {}) or {}
    node_order = [getattr(node, 'id', None) for node in getattr(getattr(savefile, 'circuit', None), 'nodes', [])]
    node_order = [node_id for node_id in node_order if isinstance(node_id, str)]
    if not node_order:
        node_order = [str(node_id) for node_id in node_results.keys() if isinstance(node_id, str)]

    spans: list[NodeExecutionSpan] = []
    outputs: dict[str, Any] = {}
    hash_nodes: list[NodeOutputHash] = []
    for index, node_id in enumerate(node_order):
        node_result = node_results.get(node_id)
        raw_status = str(getattr(node_result, 'status', 'success')).lower()
        status = 'success' if raw_status in {'success', 'completed', 'ok'} else 'failed'
        spans.append(NodeExecutionSpan(node_id=node_id, start_ms=index, end_ms=index + 1, duration_ms=1, status=status))
        output = getattr(node_result, 'output', None)
        if output is not None:
            outputs[node_id] = output
            safe_output = _to_json_safe(output)
            hash_nodes.append(NodeOutputHash(node_id=node_id, algorithm='repr', hash_value=str(abs(hash(repr(safe_output))))))

    timeline = ExecutionTimeline(execution_id=run_id, start_ms=0, end_ms=len(spans), duration_ms=len(spans), node_spans=spans)
    hash_report = ExecutionHashReport(execution_id=run_id, node_hashes=hash_nodes)
    snapshot = ExecutionSnapshotBuilder().build(execution_id=run_id, timeline=timeline, outputs=outputs, hash_report=hash_report)

    overall_status = str(getattr(trace, 'status', 'success')).lower()
    record_status = _infer_record_status(status=overall_status)
    raw_artifacts = list(getattr(trace, 'all_artifacts', []) or [])
    explicit_artifact_refs = _artifact_record_cards_from_raw_artifacts(raw_artifacts, run_id)
    trace_mapping = trace.to_dict() if hasattr(trace, 'to_dict') else None
    if not isinstance(trace_mapping, dict):
        trace_mapping = getattr(trace, '__dict__', None)
    if not isinstance(trace_mapping, dict):
        trace_mapping = {}
    routing_summary, safety_summary, confidence_summary, node_precision = _extract_precision_from_trace(trace_mapping)
    errors: list[ExecutionIssue] = []
    for node_id, node_result in node_results.items():
        error_message = getattr(node_result, 'error', None)
        if error_message:
            errors.append(ExecutionIssue(issue_code='NODE_EXECUTION_ERROR', category='runtime', severity='high', location=str(node_id), message=str(error_message)))

    created_at = _iso_now()
    started_iso = None
    finished_iso = None
    if started_at is not None:
        started_iso = datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat()
    if ended_at is not None:
        finished_iso = datetime.fromtimestamp(ended_at, tz=timezone.utc).isoformat()

    record = create_execution_record_from_snapshot(
        snapshot,
        commit_id=str(commit_id or f'uncommitted::{run_id}'),
        trigger_type='manual_run',
        working_save_id=working_save_id,
        trigger_reason='savefile_trace_materialization',
        status=record_status,
        title=getattr(getattr(savefile, 'meta', None), 'name', None),
        description=getattr(getattr(savefile, 'meta', None), 'description', None),
        created_at=created_at,
        started_at=started_iso,
        finished_at=finished_iso,
        input_summary=getattr(getattr(savefile, 'state', None), 'input', {}) or {},
        trace_ref=f'trace://{run_id}',
        event_stream_ref=None,
        final_outputs=outputs,
        artifact_refs=explicit_artifact_refs,
        errors=errors,
        provider_usage_summary={'savefile_name': getattr(getattr(savefile, 'meta', None), 'name', None)},
        trace_summary=f'Savefile trace materialized for {run_id} with {len(node_order)} node(s).',
        observability_refs=[f'trace://{run_id}'],
        routing_summary=routing_summary,
        safety_summary=safety_summary,
        confidence_summary=confidence_summary,
        node_precision=node_precision,
    )
    return serialize_execution_record(record)


def _has_serialized_execution_record_identity(record: dict[str, Any]) -> bool:
    if not isinstance(record, dict) or not record:
        return False
    meta = record.get('meta') if isinstance(record.get('meta'), dict) else {}
    source = record.get('source') if isinstance(record.get('source'), dict) else {}
    return bool(meta.get('run_id') and source.get('commit_id'))


def _payload_supports_richer_execution_record_materialization(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False

    replay_payload = payload.get('replay_payload') if isinstance(payload.get('replay_payload'), dict) else {}
    result = payload.get('result') if isinstance(payload.get('result'), dict) else {}
    trace = payload.get('trace') if isinstance(payload.get('trace'), dict) else {}

    node_order = replay_payload.get('node_order') if isinstance(replay_payload.get('node_order'), list) else []
    input_state = replay_payload.get('input_state') if isinstance(replay_payload.get('input_state'), dict) else {}
    expected_outputs = replay_payload.get('expected_outputs') if isinstance(replay_payload.get('expected_outputs'), dict) else {}
    node_results = result.get('node_results') if isinstance(result.get('node_results'), dict) else {}

    has_structural_or_trace_detail = bool(trace) or bool(node_order) or bool(node_results) or bool(input_state)
    has_output_detail = bool(expected_outputs)
    return has_structural_or_trace_detail and has_output_detail


def _is_substantive_serialized_execution_record(record: dict[str, Any]) -> bool:
    if not _has_serialized_execution_record_identity(record):
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


def materialize_execution_record_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    existing = payload.get('execution_record')
    if not _has_serialized_execution_record_identity(existing) and _has_serialized_execution_record_identity(payload):
        existing = payload
    if _is_substantive_serialized_execution_record(existing):
        return existing
    if _has_serialized_execution_record_identity(existing) and not _payload_supports_richer_execution_record_materialization(payload):
        return existing

    snapshot = _build_snapshot_from_payload(payload)
    if snapshot is None:
        return existing if _has_serialized_execution_record_identity(existing) else {}

    replay_payload = payload.get('replay_payload') if isinstance(payload.get('replay_payload'), dict) else {}
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    trace = payload.get('trace') if isinstance(payload.get('trace'), dict) else {}
    result = payload.get('result') if isinstance(payload.get('result'), dict) else {}
    existing_meta = existing.get('meta') if isinstance(existing, dict) and isinstance(existing.get('meta'), dict) else {}
    existing_source = existing.get('source') if isinstance(existing, dict) and isinstance(existing.get('source'), dict) else {}
    preferred_existing_run_id = existing_meta.get('run_id') if _has_serialized_execution_record_identity(existing) else None
    execution_id = str(preferred_existing_run_id or snapshot.execution_id)

    trace_ref = f'trace://{execution_id}' if trace else None
    event_stream_ref = f'events://{execution_id}' if trace.get('events') else None
    status = _infer_record_status(trace=trace, status=result.get('status'))

    final_outputs = snapshot.node_outputs if snapshot.node_outputs else (replay_payload.get('expected_outputs') if isinstance(replay_payload.get('expected_outputs'), dict) else {})
    record = create_execution_record_from_snapshot(
        snapshot,
        commit_id=str(existing_source.get('commit_id') or replay_payload.get('commit_id') or f'uncommitted::{execution_id}'),
        trigger_type='manual_run',
        trigger_reason='cli_payload_materialization',
        status=status,
        input_summary=replay_payload.get('input_state') if isinstance(replay_payload.get('input_state'), dict) else {},
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        final_outputs=final_outputs,
        provider_usage_summary=summary if summary else None,
        termination_reason=_termination_reason_from_trace(trace, status=status),
        pause_boundary=_pause_boundary_from_trace(trace, status=status),
        observability_refs=[item for item in [trace_ref, event_stream_ref] if item],
    )
    serialized = serialize_execution_record(record)
    payload['execution_record'] = serialized
    return serialized

def build_execution_record_reference_contract(record: ExecutionRecordModel) -> dict[str, Any]:
    primary_trace_ref = record.timeline.event_stream_ref or record.timeline.trace_ref
    node_trace_refs = {
        item.node_id: item.trace_ref
        for item in record.node_results.results
        if item.trace_ref
    }
    output_value_refs = {
        item.output_ref: item.value_ref
        for item in record.outputs.final_outputs
        if item.value_ref
    }
    artifact_ref_map = {
        item.artifact_id: item.ref
        for item in record.artifacts.artifact_refs
        if item.ref
    }
    unresolved_output_refs = [
        item.output_ref
        for item in record.outputs.final_outputs
        if not item.value_ref
    ]
    unresolved_artifact_refs = [
        item.artifact_id
        for item in record.artifacts.artifact_refs
        if not item.ref
    ]
    observability_refs = list(record.observability.observability_refs or [])
    pause_boundary = dict(record.diagnostics.pause_boundary or {}) if isinstance(record.diagnostics.pause_boundary, dict) else {}
    paused_run_state = dict(record.diagnostics.paused_run_state or {}) if isinstance(record.diagnostics.paused_run_state, dict) else {}
    resume_request = _resume_request_from_paused_run_state_payload(paused_run_state)
    trigger_type = record.source.trigger_type
    is_replay_run = trigger_type == 'replay_run'
    return {
        'run_id': record.meta.run_id,
        'commit_id': record.source.commit_id,
        'trigger_type': trigger_type,
        'is_replay_run': is_replay_run,
        'primary_trace_ref': primary_trace_ref,
        'trace_ref': record.timeline.trace_ref,
        'event_stream_ref': record.timeline.event_stream_ref,
        'node_trace_refs': node_trace_refs,
        'output_value_refs': output_value_refs,
        'artifact_refs': artifact_ref_map,
        'unresolved_output_refs': unresolved_output_refs,
        'unresolved_artifact_refs': unresolved_artifact_refs,
        'observability_refs': observability_refs,
        'termination_reason': record.diagnostics.termination_reason,
        'pause_boundary': pause_boundary or None,
        'paused_run_state': paused_run_state or None,
        'resume_request': dict(resume_request) if resume_request else None,
        'is_replay_ready': bool(primary_trace_ref and not unresolved_output_refs),
        'is_audit_ready': bool(primary_trace_ref and not unresolved_artifact_refs),
        'is_resume_ready': bool(not is_replay_run and ((pause_boundary.get('can_resume')) or resume_request)),
    }




def synthesize_execution_record_reference_contract_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    explicit_execution_record = payload.get('execution_record')
    if not _has_serialized_execution_record_identity(explicit_execution_record) and _has_serialized_execution_record_identity(payload):
        explicit_execution_record = payload
    if _is_substantive_serialized_execution_record(explicit_execution_record):
        contract = build_execution_record_reference_contract_from_serialized_record(explicit_execution_record)
        payload['execution_record_reference_contract'] = contract
        return contract

    if _payload_supports_richer_execution_record_materialization(payload):
        execution_record = materialize_execution_record_from_payload(payload)
        if isinstance(execution_record, dict) and execution_record and _has_serialized_execution_record_identity(execution_record):
            contract = build_execution_record_reference_contract_from_serialized_record(execution_record)
            payload['execution_record_reference_contract'] = contract
            return contract

    if _has_serialized_execution_record_identity(explicit_execution_record):
        contract = build_execution_record_reference_contract_from_serialized_record(explicit_execution_record)
        payload['execution_record_reference_contract'] = contract
        return contract

    execution_record = materialize_execution_record_from_payload(payload)
    if isinstance(execution_record, dict) and execution_record and _has_serialized_execution_record_identity(execution_record):
        contract = build_execution_record_reference_contract_from_serialized_record(execution_record)
        payload['execution_record_reference_contract'] = contract
        return contract

    existing = payload.get('execution_record_reference_contract')
    if isinstance(existing, dict) and existing:
        return existing

    replay_payload = payload.get('replay_payload')
    if not isinstance(replay_payload, dict) or not replay_payload:
        return {}

    execution_id = str(
        replay_payload.get('execution_id')
        or payload.get('run_id')
        or 'unknown-execution'
    )

    trace = payload.get('trace') or payload.get('execution_trace')
    has_trace = isinstance(trace, dict) and bool(trace)
    has_events = bool(isinstance(trace, dict) and trace.get('events'))

    trace_ref = f'trace://{execution_id}' if has_trace else None
    event_stream_ref = f'events://{execution_id}' if has_events else None
    primary_trace_ref = event_stream_ref or trace_ref

    node_order = replay_payload.get('node_order')
    if not isinstance(node_order, list):
        node_order = []
    node_trace_refs = {
        str(node_id): f'{primary_trace_ref}#node:{node_id}'
        for node_id in node_order
        if isinstance(node_id, str) and primary_trace_ref
    }

    expected_outputs = replay_payload.get('expected_outputs')
    if not isinstance(expected_outputs, dict):
        expected_outputs = {}
    output_value_refs = {
        str(output_ref): f'{primary_trace_ref}#output:{output_ref}'
        for output_ref in expected_outputs.keys()
        if primary_trace_ref
    }
    unresolved_output_refs = [] if primary_trace_ref else [str(output_ref) for output_ref in expected_outputs.keys()]

    artifacts = payload.get('artifacts')
    if not isinstance(artifacts, list):
        artifacts = []
    artifact_refs = {
        f'artifact_{index}': f'artifact://{execution_id}/{index}'
        for index, _ in enumerate(artifacts, start=1)
    }

    contract = {
        'run_id': execution_id,
        'commit_id': replay_payload.get('commit_id'),
        'trigger_type': 'replay_run',
        'is_replay_run': True,
        'primary_trace_ref': primary_trace_ref,
        'trace_ref': trace_ref,
        'event_stream_ref': event_stream_ref,
        'node_trace_refs': node_trace_refs,
        'output_value_refs': output_value_refs,
        'artifact_refs': artifact_refs,
        'unresolved_output_refs': unresolved_output_refs,
        'unresolved_artifact_refs': [],
        'observability_refs': [item for item in [primary_trace_ref] if item],
        'paused_run_state': None,
        'resume_request': None,
        'is_replay_ready': bool(primary_trace_ref and expected_outputs),
        'is_audit_ready': bool(primary_trace_ref),
        'is_resume_ready': False,
    }
    payload['execution_record_reference_contract'] = contract
    return contract

def summarize_execution_record_for_working_save(record: ExecutionRecordModel) -> dict[str, Any]:
    reference_contract = build_execution_record_reference_contract(record)
    return {
        'run_id': record.meta.run_id,
        'commit_id': record.source.commit_id,
        'trigger_type': record.source.trigger_type,
        'replay_run': reference_contract.get('is_replay_run', False),
        'status': record.meta.status,
        'started_at': record.meta.started_at,
        'finished_at': record.meta.finished_at,
        'output_summary': record.outputs.output_summary,
        'output_count': len(record.outputs.final_outputs),
        'output_refs': [item.output_ref for item in record.outputs.final_outputs],
        'semantic_status': record.outputs.semantic_status,
        'termination_reason': record.diagnostics.termination_reason,
        'artifact_count': record.artifacts.artifact_count,
        'artifact_ids': [item.artifact_id for item in record.artifacts.artifact_refs],
        'warning_count': len(record.diagnostics.warnings),
        'error_count': len(record.diagnostics.errors),
        'trace_ref': record.timeline.trace_ref,
        'event_stream_ref': record.timeline.event_stream_ref,
        'primary_trace_ref': reference_contract['primary_trace_ref'],
        'pause_boundary': reference_contract.get('pause_boundary'),
        'paused_run_state': reference_contract.get('paused_run_state'),
        'resume_request': reference_contract.get('resume_request'),
        'resume_ready': reference_contract.get('is_resume_ready', False),
        'replay_ready': reference_contract['is_replay_ready'],
        'audit_ready': reference_contract['is_audit_ready'],
    }


__all__ = [
    'build_execution_record_reference_contract',
    'create_serialized_execution_record_from_circuit_run',
    'create_serialized_execution_record_from_savefile_trace',
    'build_execution_record_reference_contract_from_serialized_record',
    'materialize_execution_record_from_payload',
    'create_execution_record_from_snapshot',
    'summarize_execution_record_for_working_save',
    'synthesize_execution_record_reference_contract_from_payload',
    'serialize_execution_record',
    'save_execution_record_file',
]
