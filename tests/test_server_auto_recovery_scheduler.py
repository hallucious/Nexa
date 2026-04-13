from __future__ import annotations

from src.server import AutoRecoveryFallbackCandidate, AutoRecoveryProviderHealthSignal, AutoRecoveryScoringPolicy, AutoRecoveryScheduler


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


def test_scheduler_uses_provider_health_resolver() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-down"), _run_row("run-degraded")]

    def provider_health_resolver(row):
        if row["run_id"] == "run-down":
            return AutoRecoveryProviderHealthSignal(status="down", provider_key="openai")
        return AutoRecoveryProviderHealthSignal(status="degraded", provider_key="anthropic")

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-health",
        provider_health_resolver=provider_health_resolver,
        batch_limit=10,
    )

    assert outcome.stats.scanned_count == 2
    assert outcome.stats.applied_count == 2
    assert outcome.stats.auto_retry_count == 1
    assert outcome.stats.auto_mark_review_required_count == 1
    assert writes["run-down"]["orphan_review_required"] is True
    assert writes["run-degraded"]["status"] == "queued"
    assert writes["run-degraded"]["auto_retry_base_backoff_seconds"] == 600


def test_scheduler_uses_fallback_candidates_resolver_when_primary_provider_is_down() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-fallback", provider_key="openai")]

    def provider_health_resolver(row):
        return AutoRecoveryProviderHealthSignal(status="down", provider_key=str(row.get("provider_key") or "openai"))

    def fallback_candidates_resolver(row, provider_health):
        assert provider_health is not None
        return (
            AutoRecoveryFallbackCandidate(provider_key="openai", status="down"),
            AutoRecoveryFallbackCandidate(provider_key="anthropic", status="healthy", reason_code="secondary.available"),
        )

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-fallback",
        provider_health_resolver=provider_health_resolver,
        fallback_candidates_resolver=fallback_candidates_resolver,
        batch_limit=10,
    )

    assert outcome.stats.scanned_count == 1
    assert outcome.stats.applied_count == 1
    assert outcome.stats.auto_fallback_retry_count == 1
    assert writes["run-fallback"]["status"] == "queued"
    assert writes["run-fallback"]["fallback_provider_key"] == "anthropic"
    assert outcome.applied_updates[0].action == "auto_fallback_retry"


def test_scheduler_builds_fallback_candidates_from_workspace_provider_bindings() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-binding-fallback", provider_key="openai")]

    def provider_health_resolver(row):
        return AutoRecoveryProviderHealthSignal(status="down", provider_key="openai")

    def workspace_provider_binding_rows_resolver(row):
        return (
            {"workspace_id": row["workspace_id"], "binding_id": "binding-openai", "provider_key": "openai", "enabled": True},
            {"workspace_id": row["workspace_id"], "binding_id": "binding-anthropic", "provider_key": "anthropic", "enabled": True},
            {"workspace_id": row["workspace_id"], "binding_id": "binding-gemini", "provider_key": "gemini", "enabled": False},
            {"workspace_id": "ws-other", "binding_id": "binding-other", "provider_key": "mistral", "enabled": True},
        )

    def workspace_provider_health_signals_resolver(row):
        return {
            "anthropic": AutoRecoveryProviderHealthSignal(status="healthy", provider_key="anthropic", reason_code="provider.ready"),
            "gemini": AutoRecoveryProviderHealthSignal(status="degraded", provider_key="gemini", reason_code="provider.slow"),
            "mistral": AutoRecoveryProviderHealthSignal(status="healthy", provider_key="mistral", reason_code="provider.ready"),
        }

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-binding-fallback",
        provider_health_resolver=provider_health_resolver,
        workspace_provider_binding_rows_resolver=workspace_provider_binding_rows_resolver,
        workspace_provider_health_signals_resolver=workspace_provider_health_signals_resolver,
        batch_limit=10,
    )

    assert outcome.stats.auto_fallback_retry_count == 1
    assert writes["run-binding-fallback"]["fallback_provider_key"] == "anthropic"


def test_scheduler_does_not_fallback_when_workspace_binding_has_no_alternative_provider() -> None:
    rows = [_run_row("run-binding-none", provider_key="openai")]

    def provider_health_resolver(row):
        return AutoRecoveryProviderHealthSignal(status="down", provider_key="openai")

    def workspace_provider_binding_rows_resolver(row):
        return ({"workspace_id": row["workspace_id"], "binding_id": "binding-openai", "provider_key": "openai", "enabled": True},)

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        provider_health_resolver=provider_health_resolver,
        workspace_provider_binding_rows_resolver=workspace_provider_binding_rows_resolver,
        batch_limit=10,
    )

    assert outcome.stats.auto_fallback_retry_count == 0
    assert outcome.stats.auto_mark_review_required_count == 1



def test_scheduler_prefers_highest_scoring_workspace_binding_candidate() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-scored-fallback", provider_key="openai")]

    def provider_health_resolver(row):
        return AutoRecoveryProviderHealthSignal(status="down", provider_key="openai")

    def workspace_provider_binding_rows_resolver(row):
        return (
            {"workspace_id": row["workspace_id"], "provider_key": "anthropic", "enabled": True, "cost_ratio": 1.5, "priority_weight": 0.0},
            {"workspace_id": row["workspace_id"], "provider_key": "gemini", "enabled": True, "cost_ratio": 1.0, "priority_weight": 0.2},
            {"workspace_id": row["workspace_id"], "provider_key": "mistral", "enabled": True, "cost_ratio": 1.1, "priority_weight": 0.8},
        )

    def workspace_provider_health_signals_resolver(row):
        return {
            "anthropic": AutoRecoveryProviderHealthSignal(status="healthy", provider_key="anthropic"),
            "gemini": AutoRecoveryProviderHealthSignal(status="degraded", provider_key="gemini"),
            "mistral": AutoRecoveryProviderHealthSignal(status="healthy", provider_key="mistral"),
        }

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-scored-fallback",
        provider_health_resolver=provider_health_resolver,
        workspace_provider_binding_rows_resolver=workspace_provider_binding_rows_resolver,
        workspace_provider_health_signals_resolver=workspace_provider_health_signals_resolver,
        batch_limit=10,
    )

    assert outcome.stats.auto_fallback_retry_count == 1
    assert writes["run-scored-fallback"]["fallback_provider_key"] == "mistral"


def test_scheduler_uses_workspace_scoring_policy_resolver() -> None:
    writes = {}

    def writer(row):
        writes[row["run_id"]] = dict(row)
        return row

    rows = [_run_row("run-policy-fallback", provider_key="openai")]

    def provider_health_resolver(row):
        return AutoRecoveryProviderHealthSignal(status="down", provider_key="openai")

    def workspace_provider_binding_rows_resolver(row):
        return (
            {"workspace_id": row["workspace_id"], "provider_key": "anthropic", "enabled": True, "cost_ratio": 1.5, "priority_weight": 0.1},
            {"workspace_id": row["workspace_id"], "provider_key": "mistral", "enabled": True, "cost_ratio": 1.4, "priority_weight": 0.9},
        )

    def workspace_provider_health_signals_resolver(row):
        return {
            "anthropic": AutoRecoveryProviderHealthSignal(status="healthy", provider_key="anthropic"),
            "mistral": AutoRecoveryProviderHealthSignal(status="healthy", provider_key="mistral"),
        }

    def workspace_scoring_policy_resolver(row):
        return AutoRecoveryScoringPolicy(health_weight=0.1, cost_weight=0.1, priority_weight=0.8)

    outcome = AutoRecoveryScheduler.run_batch(
        rows,
        now_iso="2026-04-13T01:00:00+00:00",
        run_record_writer=writer,
        queue_job_id_factory=lambda: "job-policy-fallback",
        provider_health_resolver=provider_health_resolver,
        workspace_provider_binding_rows_resolver=workspace_provider_binding_rows_resolver,
        workspace_provider_health_signals_resolver=workspace_provider_health_signals_resolver,
        workspace_scoring_policy_resolver=workspace_scoring_policy_resolver,
        batch_limit=10,
    )

    assert outcome.stats.auto_fallback_retry_count == 1
    assert writes["run-policy-fallback"]["fallback_provider_key"] == "mistral"
