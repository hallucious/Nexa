from __future__ import annotations

from src.server import AutoRecoveryFallbackCandidate, AutoRecoveryProviderHealthSignal, AutoRecoveryScoringPolicy, apply_auto_recovery


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


def test_apply_auto_recovery_falls_back_to_healthy_provider_when_primary_is_down() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=0, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-fallback",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="openai", status="healthy"),
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", reason_code="secondary.available"),
        ),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_fallback_retry"
    assert outcome.fallback_provider_key == "anthropic"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["status"] == "queued"
    assert outcome.updated_run_record["queue_job_id"] == "job-fallback"
    assert outcome.updated_run_record["fallback_provider_key"] == "anthropic"
    assert outcome.updated_run_record["action_log"][-2]["action"] == "fallback_scoring_evaluated"
    assert outcome.updated_run_record["action_log"][-2]["after_state"]["selected_provider_key"] == "anthropic"
    assert outcome.updated_run_record["action_log"][-1]["action"] == "auto_fallback_retry"
    assert outcome.updated_run_record["action_log"][-1]["after_state"]["fallback_provider_key"] == "anthropic"


def test_apply_auto_recovery_escalates_when_primary_is_down_and_no_fallback_exists() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=0, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(AutoRecoveryFallbackCandidate(provider_key="openai", status="healthy"),),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_mark_review_required"


def test_apply_auto_recovery_uses_fallback_after_retry_limit_when_candidate_exists() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-fallback-limit",
        provider_health=AutoRecoveryProviderHealthSignal(status="healthy", provider_key="openai"),
        fallback_candidates=(AutoRecoveryFallbackCandidate(provider_key="anthropic", status="degraded"),),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_fallback_retry"
    assert outcome.updated_run_record is not None
    assert outcome.updated_run_record["queue_job_id"] == "job-fallback-limit"
    assert outcome.updated_run_record["fallback_provider_key"] == "anthropic"


def test_apply_auto_recovery_fallback_action_log_contains_audit_fields() -> None:
    outcome = apply_auto_recovery(
        _run_row(provider_key="openai", auto_retry_count=2, auto_retry_limit=2),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-020",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai", reason_code="provider.outage"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", reason_code="secondary.available"),
        ),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_fallback_retry"
    assert outcome.updated_run_record is not None
    event = outcome.updated_run_record["action_log"][-1]
    assert event["after_state"]["fallback_from_provider"] == "openai"
    assert event["after_state"]["fallback_to_provider"] == "anthropic"
    assert event["after_state"]["fallback_reason"] == "provider_down"



def test_apply_auto_recovery_selects_best_fallback_candidate_by_health_cost_and_priority() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-best",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", cost_ratio=1.5, priority_weight=0.0),
            AutoRecoveryFallbackCandidate(provider_key="gemini", status="degraded", cost_ratio=0.8, priority_weight=1.0),
            AutoRecoveryFallbackCandidate(provider_key="mistral", status="healthy", cost_ratio=1.1, priority_weight=0.6),
        ),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_fallback_retry"
    assert outcome.fallback_provider_key == "mistral"




def test_apply_auto_recovery_emits_scoring_trace_for_fallback_selection() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-score",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", cost_ratio=1.2, priority_weight=0.4),
            AutoRecoveryFallbackCandidate(provider_key="gemini", status="degraded", cost_ratio=0.8, priority_weight=0.9),
        ),
    )

    assert outcome.applied is True
    scoring_event = outcome.updated_run_record["action_log"][-2]
    assert scoring_event["action"] == "fallback_scoring_evaluated"
    trace = scoring_event["after_state"]["scoring_trace"]
    assert len(trace) == 2
    assert any(item["selected"] for item in trace)
    assert scoring_event["after_state"]["selected_provider_key"] == outcome.fallback_provider_key


def test_apply_auto_recovery_prefers_lower_latency_when_latency_weight_is_high() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-latency",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", latency_ms=900, success_rate=0.99),
            AutoRecoveryFallbackCandidate(provider_key="gemini", status="healthy", latency_ms=120, success_rate=0.80),
        ),
        scoring_policy=AutoRecoveryScoringPolicy(health_weight=0.1, cost_weight=0.0, priority_weight=0.0, latency_weight=0.8, reliability_weight=0.1),
    )

    assert outcome.applied is True
    assert outcome.fallback_provider_key == "gemini"
    trace = outcome.updated_run_record["action_log"][-2]["after_state"]["scoring_trace"]
    selected = [entry for entry in trace if entry["selected"]]
    assert selected and selected[0]["provider"] == "gemini"
    assert all("latency_score" in entry for entry in trace)


def test_apply_auto_recovery_prefers_higher_reliability_when_reliability_weight_is_high() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-reliability",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", latency_ms=120, success_rate=0.70),
            AutoRecoveryFallbackCandidate(provider_key="gemini", status="healthy", latency_ms=300, success_rate=0.98),
        ),
        scoring_policy=AutoRecoveryScoringPolicy(health_weight=0.0, cost_weight=0.0, priority_weight=0.0, latency_weight=0.2, reliability_weight=0.8),
    )

    assert outcome.applied is True
    assert outcome.fallback_provider_key == "gemini"
    trace = outcome.updated_run_record["action_log"][-2]["after_state"]["scoring_trace"]
    selected = [entry for entry in trace if entry["selected"]]
    assert selected and selected[0]["provider"] == "gemini"
    assert all("reliability_score" in entry for entry in trace)


def test_apply_auto_recovery_uses_workspace_scoring_policy_weights() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-policy",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", cost_ratio=1.6, priority_weight=0.0),
            AutoRecoveryFallbackCandidate(provider_key="mistral", status="healthy", cost_ratio=1.3, priority_weight=0.9),
        ),
        scoring_policy=AutoRecoveryScoringPolicy(health_weight=0.2, cost_weight=0.1, priority_weight=0.7),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_fallback_retry"
    assert outcome.fallback_provider_key == "mistral"
    scoring_event = outcome.updated_run_record["action_log"][-2]
    trace = scoring_event["after_state"]["scoring_trace"]
    selected = [entry for entry in trace if entry["selected"]]
    assert selected and selected[0]["provider"] == "mistral"


def test_apply_auto_recovery_uses_default_scoring_policy_when_missing() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-default",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", cost_ratio=1.1, priority_weight=0.0),
            AutoRecoveryFallbackCandidate(provider_key="mistral", status="healthy", cost_ratio=1.2, priority_weight=0.9),
        ),
    )

    assert outcome.applied is True
    assert outcome.action == "auto_fallback_retry"
    assert outcome.fallback_provider_key in {"anthropic", "mistral"}
    scoring_event = outcome.updated_run_record["action_log"][-2]
    trace = scoring_event["after_state"]["scoring_trace"]
    assert all("health_weight" in entry for entry in trace)


def test_validate_scoring_policy_defaults_when_weights_are_invalid() -> None:
    from src.server.scoring_policy_validator import validate_scoring_policy

    result = validate_scoring_policy({
        "health_weight": -1,
        "cost_weight": 0,
        "priority_weight": 0,
        "latency_weight": 0,
        "reliability_weight": 0,
    })

    assert result.is_valid is False
    assert result.used_default is True
    total = (
        result.normalized_policy.health_weight
        + result.normalized_policy.cost_weight
        + result.normalized_policy.priority_weight
        + result.normalized_policy.latency_weight
        + result.normalized_policy.reliability_weight
    )
    assert round(total, 6) == 1.0


def test_apply_auto_recovery_normalizes_custom_scoring_policy_trace_weights() -> None:
    outcome = apply_auto_recovery(
        _run_row(auto_retry_count=2, auto_retry_limit=2, provider_key="openai"),
        now_iso="2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-normalized",
        provider_health=AutoRecoveryProviderHealthSignal(status="down", provider_key="openai"),
        fallback_candidates=(
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", cost_ratio=1.1),
            AutoRecoveryFallbackCandidate(provider_key="gemini", status="healthy", cost_ratio=0.9),
        ),
        scoring_policy={
            "health_weight": 2.0,
            "cost_weight": 1.0,
            "priority_weight": 1.0,
            "latency_weight": 0.0,
            "reliability_weight": 0.0,
        },
    )

    assert outcome.applied is True
    scoring_event = outcome.updated_run_record["action_log"][-2]
    trace = scoring_event["after_state"]["scoring_trace"]
    assert trace
    first = trace[0]
    assert first["health_weight"] == 0.5
    assert first["cost_weight"] == 0.25
    assert first["priority_weight"] == 0.25
