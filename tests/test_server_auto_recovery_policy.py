from __future__ import annotations

from src.server import AutoRecoveryProviderHealthSignal, apply_auto_recovery


def _run_row(**overrides):
    row = {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "status": "failed",
        "status_family": "terminal_failure",
        "created_at": "2026-04-13T00:00:00+00:00",
        "updated_at": "2026-04-13T00:30:00+00:00",
        "queue_job_id": "job-001",
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


def test_apply_auto_recovery_retries_failed_infra_run_under_limit() -> None:
    outcome = apply_auto_recovery(
        _run_row(),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-002",
    )

    assert outcome.applied is True
    assert outcome.action == "auto_retry"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["status"] == "queued"
    assert outcome.updated_run_record["queue_job_id"] == "job-002"
    assert outcome.updated_run_record["worker_attempt_number"] == 2
    assert outcome.updated_run_record["auto_retry_count"] == 1
    assert outcome.updated_run_record["action_log"][-1]["action"] == "auto_retry"
    assert outcome.updated_run_record["action_log"][-1]["actor_user_id"] == "system:auto-recovery"


def test_apply_auto_recovery_retries_stuck_infra_run_under_limit() -> None:
    outcome = apply_auto_recovery(
        _run_row(
            status="running",
            status_family="active",
            claimed_by_worker_ref="worker-001",
            lease_expires_at="2026-04-13T00:55:00+00:00",
        ),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-009",
    )

    assert outcome.applied is True
    assert outcome.action == "auto_retry"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["status"] == "queued"
    assert outcome.updated_run_record["claimed_by_worker_ref"] is None
    assert outcome.updated_run_record["lease_expires_at"] is None
    assert outcome.updated_run_record["queue_job_id"] == "job-009"


def test_apply_auto_recovery_escalates_to_manual_review_after_limit() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2),
        now_iso="2026-04-13T01:00:00+00:00",
    )

    assert outcome.applied is True
    assert outcome.action == "auto_mark_review_required"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["status"] == "failed"
    assert outcome.updated_run_record["orphan_review_required"] is True
    assert outcome.updated_run_record["action_log"][-1]["action"] == "auto_mark_review_required"


def test_apply_auto_recovery_leaves_non_infra_failure_unchanged() -> None:
    outcome = apply_auto_recovery(
        _run_row(latest_error_family="provider_contract_failure"),
        now_iso="2026-04-13T01:00:00+00:00",
    )

    assert outcome.applied is False
    assert outcome.updated_run_record is None
    assert outcome.reason == "no_auto_recovery_needed"


def test_apply_auto_recovery_escalates_when_provider_is_down_even_under_retry_limit() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=0, auto_retry_limit=2),
        now_iso="2026-04-13T01:00:00+00:00",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_mark_review_required"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["status"] == "failed"
    assert outcome.updated_run_record["orphan_review_required"] is True


def test_apply_auto_recovery_uses_stronger_backoff_when_provider_is_degraded() -> None:
    outcome = apply_auto_recovery(
        _run_row(
            last_auto_recovery_at="2026-04-13T00:50:00+00:00",
            auto_retry_base_backoff_seconds=300,
        ),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-degraded",
        provider_health=AutoRecoveryProviderHealthSignal(status="degraded", provider_key="openai"),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_retry"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["queue_job_id"] == "job-degraded"
    assert outcome.updated_run_record["auto_retry_base_backoff_seconds"] == 600


def test_apply_auto_recovery_keeps_existing_behavior_when_provider_is_healthy() -> None:
    outcome = apply_auto_recovery(
        _run_row(),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-healthy",
        provider_health=AutoRecoveryProviderHealthSignal(status="healthy", provider_key="openai"),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_retry"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["queue_job_id"] == "job-healthy"
    assert outcome.updated_run_record["auto_retry_base_backoff_seconds"] == 300
