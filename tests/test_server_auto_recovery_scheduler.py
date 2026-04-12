from __future__ import annotations

from src.server import AutoRecoveryScheduler


def _run_row(run_id: str, **overrides):
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
        "auto_retry_limit": 2,
        "latest_error_family": "worker_infrastructure_failure",
        "orphan_review_required": False,
        "claimed_by_worker_ref": None,
        "lease_expires_at": None,
    }
    row.update(overrides)
    return row


def test_scheduler_applies_retry_and_escalation_and_writes_rows() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [
        _run_row("run-retry"),
        _run_row("run-review", auto_retry_count=2, auto_retry_limit=2),
        _run_row("run-ignore", latest_error_family="provider_contract_failure"),
    ]

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-new",
        batch_limit=10,
    )

    assert outcome.stats.scanned_count == 3
    assert outcome.stats.applied_count == 2
    assert outcome.stats.auto_retry_count == 1
    assert outcome.stats.auto_mark_review_required_count == 1
    assert outcome.stats.skipped_count == 1
    assert writes["run-retry"]["status"] == "queued"
    assert writes["run-review"]["orphan_review_required"] is True
    assert "run-ignore" not in writes


def test_scheduler_respects_batch_limit() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-001"), _run_row("run-002")]
    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-batch",
        batch_limit=1,
    )

    assert outcome.stats.scanned_count == 1
    assert outcome.stats.applied_count == 1
    assert len(outcome.applied_updates) == 1
    assert list(writes) == ["run-001"]


def test_scheduler_accepts_zero_batch_limit() -> None:
    outcome = AutoRecoveryScheduler.run_batch(
        [_run_row("run-001")],
        now_iso="2026-04-13T01:00:00+00:00",
        batch_limit=0,
    )

    assert outcome.stats.scanned_count == 0
    assert outcome.stats.applied_count == 0
    assert outcome.applied_updates == ()
