from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable, Optional

from src.contracts.artifact_contract import TypedArtifactEnvelope
from src.contracts.nex_contract import ValidationFinding
from src.engine.execution_event import ExecutionEvent
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionIssue, ExecutionRecordModel
from src.server.boundary_models import (
    EngineArtifactReference,
    EngineCorrelationContext,
    EngineExecutionBinding,
    EngineExecutionTarget,
    EngineFailureInfo,
    EngineFinalOutput,
    EngineResultEnvelope,
    EngineRunLaunchRequest,
    EngineRunLaunchResponse,
    EngineRunStatusSnapshot,
    EngineRuntimeOptions,
    EngineSignal,
    EngineTraceEvent,
    EngineValidationEnvelope,
    EngineValidationFinding,
)


def _safe_dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _preview_text(value: Any, *, limit: int = 240) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _status_from_record_status(status: str | None) -> str:
    normalized = str(status or "unknown").lower()
    if normalized in {"running", "completed", "failed", "paused", "partial", "cancelled"}:
        return normalized
    return "unknown"


def _result_state_for_record(record: ExecutionRecordModel) -> str:
    status = _status_from_record_status(record.meta.status)
    if status == "completed":
        return "ready_success"
    if status == "partial":
        return "ready_partial"
    if status in {"failed", "cancelled"}:
        return "ready_failure"
    return "not_ready"


class EngineLaunchAdapter:
    """Thin mapping layer between product/server launch DTOs and current engine entry bindings."""

    @staticmethod
    def build_request(
        *,
        run_request_id: str,
        workspace_ref: str,
        target_type: str,
        target_ref: str,
        input_payload: Any = None,
        strict_determinism: bool = False,
        trigger_source: str = "manual",
        automation_id: str | None = None,
        auth_context_ref: str | None = None,
        requested_by_user_ref: str | None = None,
        correlation_metadata: Optional[dict[str, Any]] = None,
    ) -> EngineRunLaunchRequest:
        return EngineRunLaunchRequest(
            run_request_id=run_request_id,
            workspace_ref=workspace_ref,
            execution_target=EngineExecutionTarget(target_type=target_type, target_ref=target_ref),
            input_payload=input_payload,
            runtime_options=EngineRuntimeOptions(
                strict_determinism=strict_determinism,
                trigger_source=trigger_source,
                automation_id=automation_id,
            ),
            correlation_context=EngineCorrelationContext(
                auth_context_ref=auth_context_ref,
                requested_by_user_ref=requested_by_user_ref,
                correlation_metadata=dict(correlation_metadata or {}),
            ),
            auth_context_ref=auth_context_ref,
            requested_by_user_ref=requested_by_user_ref,
        )

    @staticmethod
    def to_execution_binding(
        request: EngineRunLaunchRequest,
        *,
        circuit: dict[str, Any],
        state: dict[str, Any],
    ) -> EngineExecutionBinding:
        launch_metadata = {
            "run_request_id": request.run_request_id,
            "workspace_ref": request.workspace_ref,
            "execution_target": {
                "target_type": request.execution_target.target_type,
                "target_ref": request.execution_target.target_ref,
            },
            "auth_context_ref": request.auth_context_ref,
            "requested_by_user_ref": request.requested_by_user_ref,
            "correlation_context": {
                "auth_context_ref": request.correlation_context.auth_context_ref,
                "requested_by_user_ref": request.correlation_context.requested_by_user_ref,
                "correlation_metadata": _safe_dict(request.correlation_context.correlation_metadata),
            },
        }
        return EngineExecutionBinding(
            circuit=deepcopy(circuit),
            state=deepcopy(state),
            strict_determinism=request.runtime_options.strict_determinism,
            trigger_source=request.runtime_options.trigger_source,
            automation_id=request.runtime_options.automation_id,
            launch_metadata=launch_metadata,
            input_payload=deepcopy(request.input_payload),
        )

    @staticmethod
    def accepted(*, run_id: str, initial_status: str = "queued") -> EngineRunLaunchResponse:
        return EngineRunLaunchResponse(
            launch_status="accepted",
            run_id=run_id,
            initial_status=initial_status,  # type: ignore[arg-type]
        )

    @staticmethod
    def rejected(
        *,
        findings: Iterable[EngineValidationFinding] = (),
        engine_error_code: str | None = None,
        engine_message: str | None = None,
    ) -> EngineRunLaunchResponse:
        return EngineRunLaunchResponse(
            launch_status="rejected",
            blocking_findings=list(findings),
            engine_error_code=engine_error_code,
            engine_message=engine_message,
        )


class ValidationFindingAdapter:
    @staticmethod
    def from_validation_finding(finding: ValidationFinding) -> EngineValidationFinding:
        return EngineValidationFinding(
            code=finding.code,
            category=finding.category,
            severity=finding.severity,
            blocking=bool(finding.blocking),
            message=finding.message,
            location=finding.location,
            hint=finding.hint,
        )

    @classmethod
    def from_findings(cls, findings: Iterable[ValidationFinding]) -> EngineValidationEnvelope:
        projected = [cls.from_validation_finding(item) for item in findings]
        blocking_count = sum(1 for item in projected if item.blocking)
        warning_count = sum(1 for item in projected if not item.blocking)
        overall_status = "blocked" if blocking_count else ("passed_with_warnings" if warning_count else "passed")
        return EngineValidationEnvelope(
            overall_status=overall_status,  # type: ignore[arg-type]
            blocking_count=blocking_count,
            warning_count=warning_count,
            findings=projected,
        )


class ArtifactReferenceAdapter:
    @staticmethod
    def from_artifact_record(card: ArtifactRecordCard, *, run_id: str | None = None) -> EngineArtifactReference:
        return EngineArtifactReference(
            artifact_id=card.artifact_id,
            artifact_type=card.artifact_type,
            run_id=run_id,
            producer_node=card.producer_node,
            ref=card.ref,
            hash=card.hash,
            lineage_refs=list(card.lineage_refs),
            trace_refs=list(card.trace_refs),
            validation_status=card.validation_status,
            metadata=deepcopy(card.metadata) if isinstance(card.metadata, dict) else None,
        )

    @staticmethod
    def from_typed_artifact_envelope(
        envelope: TypedArtifactEnvelope | dict[str, Any],
        *,
        run_id: str | None = None,
    ) -> EngineArtifactReference:
        data = envelope.to_dict() if isinstance(envelope, TypedArtifactEnvelope) else dict(envelope)
        return EngineArtifactReference(
            artifact_id=str(data.get("artifact_id") or ""),
            artifact_type=str(data.get("artifact_type") or ""),
            run_id=run_id,
            producer_node=None,
            ref=data.get("ref"),
            hash=data.get("hash"),
            lineage_refs=list(data.get("lineage_refs") or []),
            trace_refs=list(data.get("trace_refs") or []),
            validation_status=data.get("validation_status"),
            metadata=deepcopy(data.get("metadata")) if isinstance(data.get("metadata"), dict) else None,
        )


class TraceEventAdapter:
    @staticmethod
    def from_execution_event(event: ExecutionEvent, *, sequence: int = 0) -> EngineTraceEvent:
        payload = deepcopy(event.payload) if isinstance(event.payload, dict) else {}
        severity = payload.get("severity") if isinstance(payload.get("severity"), str) else None
        message = payload.get("message") if isinstance(payload.get("message"), str) else None
        return EngineTraceEvent(
            event_id=f"{event.execution_id}:{sequence}:{event.type}",
            event_type=event.type,
            sequence=sequence,
            timestamp_ms=event.timestamp_ms,
            node_id=event.node_id,
            severity=severity,
            message=message,
            payload=payload,
        )

    @staticmethod
    def from_trace_event_dict(event: dict[str, Any], *, sequence: int = 0) -> EngineTraceEvent:
        if not isinstance(event, dict):
            raise TypeError("Trace event payload must be a dict")
        event_type = str(event.get("type") or event.get("event_type") or "")
        if not event_type:
            raise ValueError("Trace event payload is missing a type")
        timestamp_ms_raw = event.get("timestamp_ms")
        if isinstance(timestamp_ms_raw, str):
            timestamp_ms = int(datetime.fromisoformat(timestamp_ms_raw.replace("Z", "+00:00")).timestamp() * 1000)
        elif isinstance(timestamp_ms_raw, (int, float)):
            timestamp_ms = int(timestamp_ms_raw)
        else:
            timestamp_ms = 0
        payload = deepcopy(event.get("payload")) if isinstance(event.get("payload"), dict) else {}
        severity = None
        if isinstance(event.get("severity"), str):
            severity = str(event.get("severity"))
        elif isinstance(payload.get("severity"), str):
            severity = str(payload.get("severity"))
        message = None
        if isinstance(event.get("message"), str):
            message = str(event.get("message"))
        elif isinstance(payload.get("message"), str):
            message = str(payload.get("message"))
        event_id = str(event.get("event_id") or event.get("id") or f"trace:{sequence}:{event_type}")
        node_id = event.get("node_id") if isinstance(event.get("node_id"), str) else None
        return EngineTraceEvent(
            event_id=event_id,
            event_type=event_type,
            sequence=sequence,
            timestamp_ms=timestamp_ms,
            node_id=node_id,
            severity=severity,
            message=message,
            payload=payload,
        )


class ExecutionRecordResultAdapter:
    @staticmethod
    def _artifact_refs(record: ExecutionRecordModel) -> list[EngineArtifactReference]:
        return [
            ArtifactReferenceAdapter.from_artifact_record(card, run_id=record.meta.run_id)
            for card in record.artifacts.artifact_refs
        ]

    @staticmethod
    def _final_output(record: ExecutionRecordModel) -> EngineFinalOutput | None:
        if not record.outputs.final_outputs:
            return None
        item = record.outputs.final_outputs[0]
        return EngineFinalOutput(
            output_key=item.output_ref,
            value_preview=_preview_text(item.value_summary or item.value_payload),
            value_type=item.value_type,
            value_ref=item.value_ref,
            source_node=item.source_node,
        )

    @staticmethod
    def _failure_info(record: ExecutionRecordModel) -> EngineFailureInfo | None:
        if record.diagnostics.errors:
            issue = record.diagnostics.errors[0]
            return EngineFailureInfo(
                code=issue.issue_code,
                message=issue.message or issue.reason or issue.issue_code,
                location=issue.location,
            )
        if record.diagnostics.termination_reason:
            return EngineFailureInfo(
                code="execution.termination_reason",
                message=str(record.diagnostics.termination_reason),
                location=record.diagnostics.failure_point,
            )
        return None

    @classmethod
    def from_execution_record(cls, record: ExecutionRecordModel) -> EngineResultEnvelope:
        result_state = _result_state_for_record(record)
        status = _status_from_record_status(record.meta.status)
        metrics = deepcopy(record.observability.metrics)
        if record.timeline.total_duration_ms is not None and "duration_ms" not in metrics:
            metrics["duration_ms"] = record.timeline.total_duration_ms
        trace_ref = record.timeline.event_stream_ref or record.timeline.trace_ref
        summary = record.outputs.output_summary or record.meta.title or f"Run {record.meta.run_id} has no final output summary"
        return EngineResultEnvelope(
            run_id=record.meta.run_id,
            final_status=status,  # type: ignore[arg-type]
            result_state=result_state,  # type: ignore[arg-type]
            result_summary=summary,
            final_output=cls._final_output(record),
            artifact_refs=cls._artifact_refs(record),
            trace_ref=trace_ref,
            metrics=metrics,
            failure_info=cls._failure_info(record),
        )


class EngineStatusProjectionAdapter:
    @staticmethod
    def _active_node(record: ExecutionRecordModel) -> tuple[str | None, str | None]:
        if record.meta.status == "paused":
            boundary = record.diagnostics.pause_boundary or {}
            pause_node = boundary.get("pause_node_id") if isinstance(boundary, dict) else None
            if isinstance(pause_node, str) and pause_node:
                return pause_node, pause_node.replace("_", " ").title()
        if record.diagnostics.failure_point:
            node_id = record.diagnostics.failure_point
            return node_id, node_id.replace("_", " ").title()
        return None, None

    @staticmethod
    def _progress(record: ExecutionRecordModel) -> tuple[int | None, str | None]:
        total = len(record.timeline.node_order)
        completed = len(record.timeline.completed_nodes)
        status = _status_from_record_status(record.meta.status)
        if total <= 0:
            return None, None
        if status == "completed":
            return 100, f"Completed {total} of {total} nodes"
        percent = max(0, min(100, int((completed / total) * 100)))
        if status == "running":
            return percent, f"Completed {completed} of {total} nodes"
        if status in {"failed", "paused", "partial", "cancelled"}:
            return percent, f"Reached {completed} of {total} nodes before {status}"
        return None, None

    @staticmethod
    def _latest_signal(record: ExecutionRecordModel) -> EngineSignal | None:
        if record.diagnostics.errors:
            issue = record.diagnostics.errors[0]
            return EngineSignal(
                severity=issue.severity,
                code=issue.issue_code,
                message=issue.message or issue.reason or issue.issue_code,
            )
        if record.diagnostics.warnings:
            issue = record.diagnostics.warnings[0]
            return EngineSignal(
                severity=issue.severity,
                code=issue.issue_code,
                message=issue.message or issue.reason or issue.issue_code,
            )
        if record.diagnostics.termination_reason:
            return EngineSignal(
                severity="info",
                code="execution.termination_reason",
                message=str(record.diagnostics.termination_reason),
            )
        return None

    @classmethod
    def from_execution_record(cls, record: ExecutionRecordModel) -> EngineRunStatusSnapshot:
        active_node_id, active_node_label = cls._active_node(record)
        progress_percent, progress_summary = cls._progress(record)
        artifact_refs = [
            ArtifactReferenceAdapter.from_artifact_record(card, run_id=record.meta.run_id)
            for card in record.artifacts.artifact_refs
        ]
        return EngineRunStatusSnapshot(
            run_id=record.meta.run_id,
            status=_status_from_record_status(record.meta.status),  # type: ignore[arg-type]
            active_node_id=active_node_id,
            active_node_label=active_node_label,
            progress_percent=progress_percent,
            progress_summary=progress_summary,
            latest_signal=cls._latest_signal(record),
            trace_ref=record.timeline.event_stream_ref or record.timeline.trace_ref,
            artifact_count=len(artifact_refs),
            artifact_refs=artifact_refs,
        )


__all__ = [
    "ArtifactReferenceAdapter",
    "EngineLaunchAdapter",
    "EngineStatusProjectionAdapter",
    "ExecutionRecordResultAdapter",
    "TraceEventAdapter",
    "ValidationFindingAdapter",
]
