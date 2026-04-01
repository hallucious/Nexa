from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from src.engine.execution_snapshot import ExecutionSnapshot
from src.engine.execution_timeline import NodeExecutionSpan
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


def _build_timing_card(span: NodeExecutionSpan) -> NodeTimingCard:
    return NodeTimingCard(
        node_id=span.node_id,
        started_at=_ms_to_iso(span.start_ms),
        finished_at=_ms_to_iso(span.end_ms),
        duration_ms=span.duration_ms,
        outcome=span.status if span.status in {"success", "failed", "skipped", "partial", "cancelled"} else "success",
    )


def _build_node_result_cards(snapshot: ExecutionSnapshot) -> list[NodeResultCard]:
    hash_map = {item.node_id: item for item in snapshot.node_hashes}
    cards: list[NodeResultCard] = []
    for span in snapshot.timeline.node_spans:
        output = snapshot.node_outputs.get(span.node_id)
        summary = None if output is None else f"Output type: {type(output).__name__}"
        metrics = None
        node_hash = hash_map.get(span.node_id)
        if node_hash is not None:
            metrics = {"output_hash": node_hash.hash_value, "hash_algorithm": node_hash.algorithm}
        cards.append(
            NodeResultCard(
                node_id=span.node_id,
                status=span.status if span.status in {"success", "failed", "skipped", "partial", "cancelled"} else "success",
                output_summary=summary,
                warning_count=0,
                error_count=1 if span.status == 'failed' else 0,
                metrics=metrics,
            )
        )
    return cards


def _build_output_cards(final_outputs: dict[str, Any] | None) -> list[OutputResultCard]:
    cards: list[OutputResultCard] = []
    for output_ref, value in (final_outputs or {}).items():
        cards.append(OutputResultCard(output_ref=output_ref, value_summary=str(value)[:500]))
    return cards


def _build_observability_metrics(snapshot: ExecutionSnapshot) -> dict[str, Any]:
    return {
        'execution_id': snapshot.execution_id,
        'duration_ms': snapshot.timeline.duration_ms,
        'node_count': len(snapshot.timeline.node_spans),
        'hashed_nodes': len(snapshot.node_hashes),
    }


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
    output_cards = _build_output_cards(final_outputs if final_outputs is not None else snapshot.node_outputs)
    artifact_card_list = list(artifact_refs or [])
    trace_summary_value = trace_summary or f"Execution {snapshot.execution_id} observed {len(snapshot.timeline.node_spans)} node span(s)."
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
        node_results=NodeResultsModel(results=_build_node_result_cards(snapshot)),
        outputs=ExecutionOutputModel(
            final_outputs=output_cards,
            output_summary=f"{len(output_cards)} output(s) recorded" if output_cards else 'No final outputs recorded',
            semantic_status='normal' if output_cards else 'empty',
        ),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=artifact_card_list,
            artifact_count=len(artifact_card_list),
            artifact_summary=f"{len(artifact_card_list)} artifact ref(s) recorded" if artifact_card_list else 'No artifact refs recorded',
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
            observability_refs=observability_refs,
        ),
    )


def summarize_execution_record_for_working_save(record: ExecutionRecordModel) -> dict[str, Any]:
    return {
        'run_id': record.meta.run_id,
        'commit_id': record.source.commit_id,
        'status': record.meta.status,
        'started_at': record.meta.started_at,
        'finished_at': record.meta.finished_at,
        'output_summary': record.outputs.output_summary,
        'artifact_count': record.artifacts.artifact_count,
        'warning_count': len(record.diagnostics.warnings),
        'error_count': len(record.diagnostics.errors),
        'trace_ref': record.timeline.trace_ref,
    }


__all__ = [
    'create_execution_record_from_snapshot',
    'summarize_execution_record_for_working_save',
    'serialize_execution_record',
    'save_execution_record_file',
]
