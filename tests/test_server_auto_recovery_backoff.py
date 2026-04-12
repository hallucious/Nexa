from __future__ import annotations

from src.server import AutoRecoveryScheduler, apply_auto_recovery


def _run_row(run_id: str = "run-001", **overrides):
    row = {
        "run_id": run_id,
        "workspace_id": "ws-001",
        "status": "failed",
        "status_family": "terminal_failure",
        "created_at": "2026-04-13T00:00:00+00:00",
        "updated_at": "2026-04-13T00:30:00+00:00",
        "queue_job_id": f"job-{run_id}",
        "worker_attempt_number": 1,
        "auto_retry_count": 0,
        "auto_retry_limit": 3,
        "auto_retry_base_backoff_seconds": 300,
        "latest_error_family": "worker_infrastructure_failure",
        "orphan_review_required": False,
        "claimed_by_worker_ref": None,
        "lease_expires_at": None,
    }
    row.update(overrides)
    return row


def test_apply_auto_recovery_skips_when_backoff_active() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=1, last_auto_recovery_at="2026-04-13T00:58:00+00:00"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-new",
    )
    assert outcome.applied is False
    assert outcome.reason == "backoff_active"


def test_apply_auto_recovery_retries_after_backoff_window() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=1, last_auto_recovery_at="2026-04-13T00:45:00+00:00"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-new",
    )
    assert outcome.applied is True
    assert outcome.action == "auto_retry"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["queue_job_id"] == "job-new"


def test_scheduler_respects_max_applied_per_batch() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-001"), _run_row("run-002"), _run_row("run-003")]
    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-batch",
        batch_limit=10,
        max_applied_per_batch=2,
    )
    assert outcome.stats.applied_count == 2
    assert len(writes) == 2
