from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.engine.execution_artifact_hashing import ExecutionHashReport, NodeOutputHash
from src.engine.execution_snapshot import ExecutionSnapshot, ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
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
    if status == 'partial':
        return 'partial'
    if status in {'failed', 'cancelled'}:
        return 'failed' if not has_outputs else 'partial'
    return 'normal' if has_outputs else 'failed'


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


def _build_node_result_cards(
    snapshot: ExecutionSnapshot,
    *,
    trace_ref: str | None,
    event_stream_ref: str | None,
    artifact_id_by_node: dict[str, str],
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
        artifact_refs = []
        artifact_id = artifact_id_by_node.get(span.node_id)
        if artifact_id is not None:
            artifact_refs.append(artifact_id)
        cards.append(
            NodeResultCard(
                node_id=span.node_id,
                status=span.status if span.status in {"success", "failed", "skipped", "partial", "cancelled"} else "success",
                output_summary=summary,
                output_type=output_type,
                output_preview=output_preview,
                artifact_refs=artifact_refs,
                warning_count=0,
                error_count=1 if span.status == 'failed' else 0,
                trace_ref=_node_trace_ref(trace_ref, event_stream_ref, span.node_id),
                metrics=metrics,
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
    provider_usage_summary: dict[str, Any] | None = None,
    plugin_usage_summary: dict[str, Any] | None = None,
    trace_summary: str | None = None,
    observability_refs: list[str] | None = None,
) -> ExecutionRecordModel:
    created = created_at or _iso_now()
    started = started_at or _ms_to_iso(snapshot.timeline.start_ms) or created
    finished = finished_at or _ms_to_iso(snapshot.timeline.end_ms)
    timing_cards = [_build_timing_card(span) for span in snapshot.timeline.node_spans]
    node_order = [span.node_id for span in snapshot.timeline.node_spans]
    output_cards = _build_output_cards(final_outputs if final_outputs is not None else snapshot.node_outputs, trace_ref=trace_ref)
    artifact_card_list = _build_artifact_cards(snapshot, artifact_refs, output_cards)
    artifact_id_by_node = {
        card.producer_node: card.artifact_id
        for card in artifact_card_list
        if card.producer_node
    }
    node_result_cards = _build_node_result_cards(
        snapshot,
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        artifact_id_by_node=artifact_id_by_node,
    )
    trace_summary_value = trace_summary or f'Execution {snapshot.execution_id} observed {len(snapshot.timeline.node_spans)} node span(s).'
    resolved_observability_refs = _merge_observability_refs(
        observability_refs,
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        artifact_cards=artifact_card_list,
    )
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
        ),
        observability=ExecutionObservabilityModel(
            metrics=_build_observability_metrics(snapshot),
            provider_usage_summary=provider_usage_summary,
            plugin_usage_summary=plugin_usage_summary,
            trace_summary=trace_summary_value,
            observability_refs=resolved_observability_refs,
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
    return {
        'run_id': meta.get('run_id'),
        'commit_id': source.get('commit_id'),
        'primary_trace_ref': primary_trace_ref,
        'trace_ref': timeline.get('trace_ref'),
        'event_stream_ref': timeline.get('event_stream_ref'),
        'node_trace_refs': node_trace_refs,
        'output_value_refs': output_value_refs,
        'artifact_refs': artifact_refs,
        'unresolved_output_refs': unresolved_output_refs,
        'unresolved_artifact_refs': unresolved_artifact_refs,
        'observability_refs': observability_refs,
        'is_replay_ready': bool(primary_trace_ref and not unresolved_output_refs),
        'is_audit_ready': bool(primary_trace_ref and not unresolved_artifact_refs),
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
        artifact_type = type(artifact).__name__
        artifact_ref = None
        summary_source = artifact
        if isinstance(artifact, dict):
            artifact_type = str(artifact.get('type') or artifact.get('artifact_type') or artifact_type)
            artifact_ref = artifact.get('ref') if isinstance(artifact.get('ref'), str) else None
            summary_source = artifact.get('summary') if artifact.get('summary') is not None else artifact
        cards.append(
            ArtifactRecordCard(
                artifact_id=f'artifact::raw::{index}',
                artifact_type=artifact_type,
                ref=artifact_ref or f'artifact://{execution_id}/raw/{index}',
                summary=_summarize_value(summary_source),
            )
        )
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

    created_at = _iso_now()
    started_iso = None
    finished_iso = None
    if started_at is not None:
        started_iso = datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat()
    if ended_at is not None:
        finished_iso = datetime.fromtimestamp(ended_at, tz=timezone.utc).isoformat()

    record = create_execution_record_from_snapshot(
        snapshot,
        commit_id=str(commit_id or f'uncommitted::{resolved_execution_id}'),
        trigger_type='manual_run',
        trigger_reason='circuit_run_materialization',
        status='completed',
        title=str(circuit.get('id') or 'circuit-run'),
        input_summary=input_state or {},
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        final_outputs=outputs,
        artifact_refs=explicit_artifact_refs,
        provider_usage_summary={'circuit_id': circuit.get('id')},
        trace_summary=f'Circuit run materialized for {resolved_execution_id} with {len(node_order)} node(s).',
        observability_refs=[item for item in [trace_ref, event_stream_ref] if item],
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
    record_status = 'failed' if overall_status in {'failure', 'failed', 'error'} else 'completed'
    raw_artifacts = list(getattr(trace, 'all_artifacts', []) or [])
    explicit_artifact_refs = _artifact_record_cards_from_raw_artifacts(raw_artifacts, run_id)
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
    )
    return serialize_execution_record(record)


def _is_minimal_serialized_execution_record(record: dict[str, Any]) -> bool:
    if not isinstance(record, dict) or not record:
        return False
    meta = record.get('meta') if isinstance(record.get('meta'), dict) else {}
    source = record.get('source') if isinstance(record.get('source'), dict) else {}
    return bool(meta.get('run_id') and source.get('commit_id'))


def materialize_execution_record_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    existing = payload.get('execution_record')
    if _is_minimal_serialized_execution_record(existing):
        return existing

    snapshot = _build_snapshot_from_payload(payload)
    if snapshot is None:
        return {}

    replay_payload = payload.get('replay_payload') if isinstance(payload.get('replay_payload'), dict) else {}
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    trace = payload.get('trace') if isinstance(payload.get('trace'), dict) else {}
    result = payload.get('result') if isinstance(payload.get('result'), dict) else {}
    execution_id = snapshot.execution_id

    trace_ref = f'trace://{execution_id}' if trace else None
    event_stream_ref = f'events://{execution_id}' if trace.get('events') else None
    status_raw = result.get('status')
    status = 'completed'
    if isinstance(status_raw, str) and status_raw.lower() in {'failure','failed','error'}:
        status = 'failed'

    final_outputs = replay_payload.get('expected_outputs') if isinstance(replay_payload.get('expected_outputs'), dict) and replay_payload.get('expected_outputs') else snapshot.node_outputs
    record = create_execution_record_from_snapshot(
        snapshot,
        commit_id=str(replay_payload.get('commit_id') or f'uncommitted::{execution_id}'),
        trigger_type='manual_run',
        trigger_reason='cli_payload_materialization',
        status=status,
        input_summary=replay_payload.get('input_state') if isinstance(replay_payload.get('input_state'), dict) else {},
        trace_ref=trace_ref,
        event_stream_ref=event_stream_ref,
        final_outputs=final_outputs,
        provider_usage_summary=summary if summary else None,
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
    return {
        'run_id': record.meta.run_id,
        'commit_id': record.source.commit_id,
        'primary_trace_ref': primary_trace_ref,
        'trace_ref': record.timeline.trace_ref,
        'event_stream_ref': record.timeline.event_stream_ref,
        'node_trace_refs': node_trace_refs,
        'output_value_refs': output_value_refs,
        'artifact_refs': artifact_ref_map,
        'unresolved_output_refs': unresolved_output_refs,
        'unresolved_artifact_refs': unresolved_artifact_refs,
        'observability_refs': observability_refs,
        'is_replay_ready': bool(primary_trace_ref and not unresolved_output_refs),
        'is_audit_ready': bool(primary_trace_ref and not unresolved_artifact_refs),
    }




def synthesize_execution_record_reference_contract_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    existing = payload.get('execution_record_reference_contract')
    if isinstance(existing, dict) and existing:
        return existing

    execution_record = payload.get('execution_record')
    if not (isinstance(execution_record, dict) and execution_record):
        execution_record = materialize_execution_record_from_payload(payload)

    if isinstance(execution_record, dict) and execution_record:
        contract = build_execution_record_reference_contract_from_serialized_record(execution_record)
        payload['execution_record_reference_contract'] = contract
        return contract

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
        'primary_trace_ref': primary_trace_ref,
        'trace_ref': trace_ref,
        'event_stream_ref': event_stream_ref,
        'node_trace_refs': node_trace_refs,
        'output_value_refs': output_value_refs,
        'artifact_refs': artifact_refs,
        'unresolved_output_refs': unresolved_output_refs,
        'unresolved_artifact_refs': [],
        'observability_refs': [item for item in [primary_trace_ref] if item],
        'is_replay_ready': bool(primary_trace_ref and expected_outputs),
        'is_audit_ready': bool(primary_trace_ref),
    }
    payload['execution_record_reference_contract'] = contract
    return contract

def summarize_execution_record_for_working_save(record: ExecutionRecordModel) -> dict[str, Any]:
    reference_contract = build_execution_record_reference_contract(record)
    return {
        'run_id': record.meta.run_id,
        'commit_id': record.source.commit_id,
        'status': record.meta.status,
        'started_at': record.meta.started_at,
        'finished_at': record.meta.finished_at,
        'output_summary': record.outputs.output_summary,
        'output_count': len(record.outputs.final_outputs),
        'output_refs': [item.output_ref for item in record.outputs.final_outputs],
        'semantic_status': record.outputs.semantic_status,
        'artifact_count': record.artifacts.artifact_count,
        'artifact_ids': [item.artifact_id for item in record.artifacts.artifact_refs],
        'warning_count': len(record.diagnostics.warnings),
        'error_count': len(record.diagnostics.errors),
        'trace_ref': record.timeline.trace_ref,
        'event_stream_ref': record.timeline.event_stream_ref,
        'primary_trace_ref': reference_contract['primary_trace_ref'],
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
