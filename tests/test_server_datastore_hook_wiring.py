from __future__ import annotations

import json
from typing import Any, Mapping

import pytest

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.edge_rate_limit_runtime import RedisEdgeRateLimiter
from src.server.otel_datastore_runtime import OTEL_DATASTORE_EVENT_TYPE
from src.server.pg import run_submission_store_pg


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = int(seconds)
        return True

    def ttl(self, key: str) -> int:
        return self.expirations.get(key, 0)


class _FailingRedis:
    def incr(self, key: str) -> int:
        raise RuntimeError("redis unavailable with sk-redis-secret")


class _FakeResult:
    def __init__(self, *, rowcount: int = 1, row: Mapping[str, Any] | None = None) -> None:
        self.rowcount = rowcount
        self._row = row

    def fetchone(self) -> Mapping[str, Any] | None:
        return self._row

    def fetchall(self) -> list[Mapping[str, Any]]:
        return [self._row] if self._row is not None else []


class _FakeConnection:
    def __init__(self, result: _FakeResult) -> None:
        self.result = result
        self.calls: list[tuple[Any, Mapping[str, Any]]] = []

    def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        self.calls.append((sql, params))
        return self.result

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class _FailingConnection:
    def execute(self, sql: Any, params: Mapping[str, Any]) -> _FakeResult:
        raise RuntimeError("postgres failed with sk-db-secret")

    def __enter__(self) -> "_FailingConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class _FakeEngine:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def begin(self) -> Any:
        return self.connection

    def connect(self) -> Any:
        return self.connection


def test_redis_edge_rate_limiter_emits_safe_datastore_span() -> None:
    emitted: list[dict[str, Any]] = []
    limiter = RedisEdgeRateLimiter(
        redis_client=_FakeRedis(),
        requests_per_window=2,
        window_seconds=30,
        key_prefix="nexa:test:rate-limit",
        datastore_span_writer=emitted.append,
    )

    assert limiter.record("POST:/api/runs:sk-user-secret") == (True, 0)

    serialized = json.dumps(emitted, sort_keys=True)
    assert "sk-user-secret" not in serialized
    assert "POST:/api/runs" not in serialized
    assert emitted[0]["event_type"] == OTEL_DATASTORE_EVENT_TYPE
    assert emitted[0]["name"] == "redis.rate_limit.command"
    assert emitted[0]["attributes"]["db.system"] == "redis"
    assert emitted[0]["attributes"]["db.operation"] == "INCR"
    assert emitted[0]["attributes"]["db.redis.key_prefix"] == "nexa:test:rate-limit"
    assert len(emitted[0]["attributes"]["db.redis.key_hash"]) == 16
    assert emitted[0]["attributes"]["nexa.rate_limit.allowed"] is True


def test_redis_edge_rate_limiter_redacts_exception_event() -> None:
    emitted: list[dict[str, Any]] = []
    limiter = RedisEdgeRateLimiter(
        redis_client=_FailingRedis(),
        requests_per_window=1,
        window_seconds=45,
        fail_open=False,
        datastore_span_writer=emitted.append,
    )

    assert limiter.record("GET:/api/runs:sk-user-secret") == (False, 45)

    serialized = json.dumps(emitted, sort_keys=True)
    assert "sk-user-secret" not in serialized
    assert "sk-redis-secret" not in serialized
    assert emitted[0]["event_type"] == OTEL_DATASTORE_EVENT_TYPE
    assert emitted[0]["attributes"]["db.system"] == "redis"
    assert emitted[0]["events"][0]["attributes"]["exception.message"] == REDACTED_VALUE


def test_postgres_run_submission_store_emits_safe_datastore_span(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_submission_store_pg, "text", lambda sql: sql)
    emitted: list[dict[str, Any]] = []
    engine = _FakeEngine(_FakeConnection(_FakeResult(rowcount=1)))
    store = run_submission_store_pg.PostgresRunSubmissionStore(engine, otel_span_writer=emitted.append)

    assert store.mark_queued(
        run_id="run-sk-secret",
        queue_job_id="job-001",
        queue_name="q-default",
    ) is True

    serialized = json.dumps(emitted, sort_keys=True)
    assert "run-sk-secret" not in serialized
    assert "job-001" not in serialized
    assert "UPDATE run_submissions" not in serialized
    assert emitted[0]["event_type"] == OTEL_DATASTORE_EVENT_TYPE
    assert emitted[0]["name"] == "db.run_submissions.query"
    assert emitted[0]["attributes"]["db.system"] == "postgresql"
    assert emitted[0]["attributes"]["db.operation"] == "UPDATE"
    assert emitted[0]["attributes"]["db.sql.table"] == "run_submissions"
    assert emitted[0]["attributes"]["db.query.label"] == "run_submissions.mark_queued"
    assert emitted[0]["attributes"]["db.statement"] == REDACTED_VALUE
    assert emitted[0]["attributes"]["db.query.parameters"] == REDACTED_VALUE
    assert emitted[0]["attributes"]["db.rows_affected"] == 1


def test_postgres_run_submission_store_redacts_exception_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_submission_store_pg, "text", lambda sql: sql)
    emitted: list[dict[str, Any]] = []
    store = run_submission_store_pg.PostgresRunSubmissionStore(
        _FakeEngine(_FailingConnection()),
        otel_span_writer=emitted.append,
    )

    with pytest.raises(RuntimeError, match="postgres failed"):
        store.mark_claimed(run_id="run-sk-secret")

    serialized = json.dumps(emitted, sort_keys=True)
    assert "run-sk-secret" not in serialized
    assert "sk-db-secret" not in serialized
    assert "UPDATE run_submissions" not in serialized
    assert emitted[0]["event_type"] == OTEL_DATASTORE_EVENT_TYPE
    assert emitted[0]["attributes"]["db.query.label"] == "run_submissions.mark_claimed"
    assert emitted[0]["attributes"]["db.statement"] == REDACTED_VALUE
    assert emitted[0]["attributes"]["db.query.parameters"] == REDACTED_VALUE
    assert emitted[0]["events"][0]["attributes"]["exception.message"] == REDACTED_VALUE
