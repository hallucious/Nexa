from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from uuid import uuid4

from src.engine.execution_event import ExecutionEvent
from src.server.adapters import ArtifactReferenceAdapter, ExecutionRecordResultAdapter, TraceEventAdapter
from src.server.run_admission_models import RunAdmissionOutcome
from src.server.worker_queue_models import (
    QueueJobProjection,
    QueueSubmission,
    WorkerClaim,
    WorkerLeasePolicy,
    WorkerOrphanReview,
    WorkerProjectionBundle,
)
from src.storage.models.execution_record_model import ExecutionRecordModel


def _parse_iso(iso_value: str) -> datetime:
    return datetime.fromisoformat(iso_value.replace("Z", "+00:00"))


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _now_iso() -> str:
    return _iso(datetime.now(timezone.utc))


def _lease_expiry(now_iso: str, lease_seconds: int) -> str:
    return _iso(_parse_iso(now_iso) + timedelta(seconds=lease_seconds))


def _status_family(status: str) -> str:
    normalized = (status or "unknown").strip().lower()
    if normalized in {"queued", "starting"}:
        return "pending"
    if normalized in {"running"}:
        return "active"
    if normalized in {"completed"}:
        return "terminal_success"
    if normalized in {"failed", "cancelled"}:
        return "terminal_failure"
    if normalized in {"partial", "paused"}:
        return "terminal_partial"
    return "unknown"


def _result_state_from_status(status: str) -> Optional[str]:
    normalized = (status or "unknown").strip().lower()
    if normalized == "completed":
        return "ready_success"
    if normalized == "partial":
        return "ready_partial"
    if normalized in {"failed", "cancelled"}:
        return "ready_failure"
    return None


class WorkerQueueOrchestrationService:
    @staticmethod
    def enqueue_admitted_run(
        admission: RunAdmissionOutcome,
        *,
        queue_name: str = "server_runs",
        queue_job_id_factory: Optional[callable] = None,
        now_iso: Optional[str] = None,
    ) -> QueueSubmission:
        if not admission.accepted or admission.engine_request is None or admission.run_record is None:
            raise ValueError("enqueue_admitted_run requires an accepted admission outcome with engine_request and run_record")
        queue_job_id_factory = queue_job_id_factory or (lambda: f"job_{uuid4().hex}")
        now_value = now_iso or _now_iso()
        queue_job = QueueJobProjection(
            queue_job_id=queue_job_id_factory(),
            run_id=admission.run_record.run_id,
            workspace_id=admission.run_record.workspace_id,
            run_request_id=admission.run_record.launch_request_id,
            queue_state="queued",
            queue_name=queue_name,
            priority=admission.engine_request.correlation_context.correlation_metadata.get("launch_priority", "normal"),
            enqueued_at=now_value,
            available_at=now_value,
            created_at=now_value,
            updated_at=now_value,
            worker_attempt_number=0,
        )
        run_record_row = admission.run_record.to_row()
        run_record_row.update(
            {
                "queue_job_id": queue_job.queue_job_id,
                "claimed_by_worker_ref": None,
                "claimed_at": None,
                "lease_expires_at": None,
                "last_heartbeat_at": None,
                "worker_attempt_number": 0,
                "orphan_review_required": False,
                "updated_at": now_value,
            }
        )
        return QueueSubmission(queue_job=queue_job, run_record_row=run_record_row, engine_request=admission.engine_request)

    @staticmethod
    def claim_submitted_run(
        submission: QueueSubmission,
        *,
        worker_ref: str,
        lease_policy: WorkerLeasePolicy = WorkerLeasePolicy(),
        now_iso: Optional[str] = None,
    ) -> WorkerClaim:
        now_value = now_iso or _now_iso()
        if submission.queue_job.queue_state != "queued":
            raise ValueError("Only queued submissions may be claimed")
        queue_job = QueueJobProjection(
            **{
                **submission.queue_job.to_row(),
                "queue_state": "claimed",
                "claimed_by_worker_ref": worker_ref,
                "claimed_at": now_value,
                "last_heartbeat_at": now_value,
                "lease_expires_at": _lease_expiry(now_value, lease_policy.lease_duration_s),
                "worker_attempt_number": submission.queue_job.worker_attempt_number + 1,
                "updated_at": now_value,
            }
        )
        run_record_row = deepcopy(submission.run_record_row)
        run_record_row.update(
            {
                "status": "starting",
                "status_family": "pending",
                "queue_job_id": queue_job.queue_job_id,
                "claimed_by_worker_ref": worker_ref,
                "claimed_at": now_value,
                "lease_expires_at": queue_job.lease_expires_at,
                "last_heartbeat_at": now_value,
                "worker_attempt_number": queue_job.worker_attempt_number,
                "orphan_review_required": False,
                "updated_at": now_value,
            }
        )
        return WorkerClaim(
            worker_ref=worker_ref,
            queue_job=queue_job,
            run_record_row=run_record_row,
            engine_request=submission.engine_request,
            lease_policy=lease_policy,
        )

    @staticmethod
    def refresh_heartbeat(
        claim: WorkerClaim,
        *,
        now_iso: Optional[str] = None,
    ) -> WorkerClaim:
        now_value = now_iso or _now_iso()
        queue_job = QueueJobProjection(
            **{
                **claim.queue_job.to_row(),
                "last_heartbeat_at": now_value,
                "lease_expires_at": _lease_expiry(now_value, claim.lease_policy.heartbeat_extension_s),
                "updated_at": now_value,
            }
        )
        run_record_row = deepcopy(claim.run_record_row)
        run_record_row.update(
            {
                "last_heartbeat_at": now_value,
                "lease_expires_at": queue_job.lease_expires_at,
                "updated_at": now_value,
            }
        )
        return WorkerClaim(
            worker_ref=claim.worker_ref,
            queue_job=queue_job,
            run_record_row=run_record_row,
            engine_request=claim.engine_request,
            lease_policy=claim.lease_policy,
        )

    @staticmethod
    def review_orphaned_claim(claim: WorkerClaim, *, now_iso: Optional[str] = None) -> WorkerOrphanReview:
        now_value = now_iso or _now_iso()
        lease_expires_at = claim.queue_job.lease_expires_at
        if not lease_expires_at:
            return WorkerOrphanReview(run_id=claim.queue_job.run_id, queue_job_id=claim.queue_job.queue_job_id, is_orphaned=False)
        if _parse_iso(now_value) <= _parse_iso(lease_expires_at):
            return WorkerOrphanReview(run_id=claim.queue_job.run_id, queue_job_id=claim.queue_job.queue_job_id, is_orphaned=False)
        if str(claim.run_record_row.get("status", "")).lower() in {"completed", "failed", "partial", "cancelled"}:
            return WorkerOrphanReview(run_id=claim.queue_job.run_id, queue_job_id=claim.queue_job.queue_job_id, is_orphaned=False)
        return WorkerOrphanReview(
            run_id=claim.queue_job.run_id,
            queue_job_id=claim.queue_job.queue_job_id,
            is_orphaned=True,
            reason_code="worker.orphaned_claim_detected",
            message="Worker lease expired before a terminal run projection was written.",
        )

    @staticmethod
    def recover_orphaned_claim(
        claim: WorkerClaim,
        review: WorkerOrphanReview,
        *,
        queue_job_id_factory: Optional[callable] = None,
        now_iso: Optional[str] = None,
    ) -> WorkerProjectionBundle:
        now_value = now_iso or _now_iso()
        if not review.is_orphaned:
            raise ValueError("recover_orphaned_claim requires an orphaned review")
        if claim.lease_policy.requeue_orphans and claim.queue_job.worker_attempt_number < claim.lease_policy.max_worker_attempts:
            queue_job_id_factory = queue_job_id_factory or (lambda: f"job_{uuid4().hex}")
            requeued_job = QueueJobProjection(
                queue_job_id=queue_job_id_factory(),
                run_id=claim.queue_job.run_id,
                workspace_id=claim.queue_job.workspace_id,
                run_request_id=claim.queue_job.run_request_id,
                queue_state="queued",
                queue_name=claim.queue_job.queue_name,
                priority=claim.queue_job.priority,
                enqueued_at=now_value,
                available_at=now_value,
                created_at=now_value,
                updated_at=now_value,
                worker_attempt_number=claim.queue_job.worker_attempt_number,
            )
            run_row = deepcopy(claim.run_record_row)
            run_row.update(
                {
                    "status": "queued",
                    "status_family": "pending",
                    "queue_job_id": requeued_job.queue_job_id,
                    "claimed_by_worker_ref": None,
                    "claimed_at": None,
                    "lease_expires_at": None,
                    "last_heartbeat_at": None,
                    "orphan_review_required": True,
                    "latest_error_family": "worker_infrastructure_failure",
                    "updated_at": now_value,
                }
            )
            return WorkerProjectionBundle(
                run_record_row=run_row,
                queue_job_row=requeued_job.to_row(),
                failure_family="worker_infrastructure_failure",
            )
        return WorkerQueueOrchestrationService.mark_infrastructure_failure(
            claim,
            reason_code=review.reason_code or "worker.orphaned_claim_detected",
            message=review.message or "Worker claim became orphaned.",
            now_iso=now_value,
        )

    @staticmethod
    def complete_claimed_run(
        claim: WorkerClaim,
        *,
        execution_record: ExecutionRecordModel,
        trace_events: Iterable[ExecutionEvent | dict[str, Any]] = (),
        now_iso: Optional[str] = None,
    ) -> WorkerProjectionBundle:
        now_value = now_iso or execution_record.meta.finished_at or _now_iso()
        result_envelope = ExecutionRecordResultAdapter.from_execution_record(execution_record)
        artifact_rows = tuple(
            {
                "artifact_id": item.artifact_id,
                "workspace_id": claim.run_record_row["workspace_id"],
                "run_id": execution_record.meta.run_id,
                "artifact_type": item.artifact_type,
                "producer_node": item.producer_node,
                "content_hash": item.hash,
                "storage_ref": item.ref,
                "payload_preview": item.metadata.get("label") if isinstance(item.metadata, dict) else None,
                "trace_ref": item.trace_refs[0] if item.trace_refs else None,
                "metadata_json": deepcopy(item.metadata) if isinstance(item.metadata, dict) else None,
                "created_at": now_value,
            }
            for item in result_envelope.artifact_refs
        )
        projected_trace_rows = []
        for sequence, event in enumerate(trace_events):
            if isinstance(event, ExecutionEvent):
                projected = TraceEventAdapter.from_execution_event(event, sequence=sequence)
            else:
                projected = TraceEventAdapter.from_trace_event_dict(event, sequence=sequence)
            projected_trace_rows.append(
                {
                    "trace_event_ref": projected.event_id,
                    "workspace_id": claim.run_record_row["workspace_id"],
                    "run_id": execution_record.meta.run_id,
                    "event_type": projected.event_type,
                    "node_id": projected.node_id,
                    "severity": projected.severity,
                    "message_preview": projected.message,
                    "occurred_at": datetime.fromtimestamp(projected.timestamp_ms / 1000, tz=timezone.utc).isoformat(),
                }
            )
        final_status = result_envelope.final_status
        failure_family = None
        latest_error_family = None
        if final_status == "failed":
            failure_family = "engine_execution_failure"
            latest_error_family = "engine_execution_failure"
        elif final_status == "partial":
            failure_family = "engine_partial_result"
            latest_error_family = "engine_partial_result"
        run_row = deepcopy(claim.run_record_row)
        run_row.update(
            {
                "status": final_status,
                "status_family": _status_family(final_status),
                "result_state": result_envelope.result_state,
                "latest_error_family": latest_error_family,
                "trace_available": bool(projected_trace_rows or result_envelope.trace_ref),
                "artifact_count": len(artifact_rows),
                "trace_event_count": len(projected_trace_rows),
                "started_at": run_row.get("started_at") or claim.queue_job.claimed_at,
                "finished_at": now_value,
                "updated_at": now_value,
                "orphan_review_required": False,
            }
        )
        queue_row = claim.queue_job.to_row()
        queue_row.update({"queue_state": "completed", "updated_at": now_value})
        return WorkerProjectionBundle(
            run_record_row=run_row,
            queue_job_row=queue_row,
            result_row={
                "run_id": result_envelope.run_id,
                "workspace_id": claim.run_record_row["workspace_id"],
                "final_status": result_envelope.final_status,
                "result_state": result_envelope.result_state,
                "result_summary": result_envelope.result_summary,
                "trace_ref": result_envelope.trace_ref,
                "artifact_count": len(result_envelope.artifact_refs),
                "failure_info": asdict(result_envelope.failure_info) if result_envelope.failure_info is not None else None,
                "final_output": asdict(result_envelope.final_output) if result_envelope.final_output is not None else None,
                "metrics": deepcopy(result_envelope.metrics),
                "updated_at": now_value,
            },
            artifact_rows=artifact_rows,
            trace_rows=tuple(projected_trace_rows),
            failure_family=failure_family,
        )

    @staticmethod
    def mark_infrastructure_failure(
        claim: WorkerClaim,
        *,
        reason_code: str,
        message: str,
        now_iso: Optional[str] = None,
    ) -> WorkerProjectionBundle:
        now_value = now_iso or _now_iso()
        run_row = deepcopy(claim.run_record_row)
        run_row.update(
            {
                "status": "failed",
                "status_family": "terminal_failure",
                "result_state": "ready_failure",
                "latest_error_family": "worker_infrastructure_failure",
                "finished_at": now_value,
                "updated_at": now_value,
                "orphan_review_required": False,
            }
        )
        queue_row = claim.queue_job.to_row()
        queue_row.update({"queue_state": "abandoned", "updated_at": now_value})
        return WorkerProjectionBundle(
            run_record_row=run_row,
            queue_job_row=queue_row,
            result_row={
                "run_id": claim.queue_job.run_id,
                "workspace_id": claim.run_record_row["workspace_id"],
                "final_status": "failed",
                "result_state": "ready_failure",
                "result_summary": message,
                "trace_ref": None,
                "artifact_count": 0,
                "failure_info": {"code": reason_code, "message": message, "location": None},
                "final_output": None,
                "metrics": {},
                "updated_at": now_value,
            },
            failure_family="worker_infrastructure_failure",
        )
