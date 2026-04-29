from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

from src.server.otel_datastore_runtime import (
    OtelDatastoreSpanWriter,
    build_otel_datastore_exception_event,
    build_otel_redis_span_attributes,
    emit_otel_datastore_span,
)


EDGE_RATE_LIMIT_BACKEND_MEMORY = "memory"
EDGE_RATE_LIMIT_BACKEND_REDIS = "redis"
EDGE_RATE_LIMIT_BACKENDS = {EDGE_RATE_LIMIT_BACKEND_MEMORY, EDGE_RATE_LIMIT_BACKEND_REDIS}
EDGE_RATE_LIMIT_REDIS_UNAVAILABLE_REASON = "edge_rate_limit_redis_unavailable"
EDGE_RATE_LIMIT_REDIS_ERROR_REASON = "edge_rate_limit_redis_error"


class EdgeRateLimiter(Protocol):
    def record(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        """Record one request and return (allowed, retry_after_seconds)."""


@dataclass(frozen=True)
class EdgeRateLimitBackendStatus:
    backend: str
    available: bool
    fail_open: bool
    reason: str | None = None

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "backend": self.backend,
            "available": self.available,
            "fail_open": self.fail_open,
        }
        if self.reason:
            payload["reason"] = self.reason
        return payload


def normalize_rate_limit_backend(value: str | None) -> str:
    backend = str(value or EDGE_RATE_LIMIT_BACKEND_MEMORY).strip().lower()
    if backend not in EDGE_RATE_LIMIT_BACKENDS:
        raise ValueError(f"Unsupported edge rate limit backend: {backend}")
    return backend


def redis_rate_limit_key(*, namespace: str, identity: str, window_seconds: int) -> str:
    normalized_namespace = str(namespace or "nexa:edge:rate-limit").strip() or "nexa:edge:rate-limit"
    normalized_identity = str(identity or "anonymous").strip() or "anonymous"
    normalized_identity = normalized_identity.replace("\n", " ").replace("\r", " ")
    return f"{normalized_namespace}:{int(window_seconds)}:{normalized_identity}"


class RedisEdgeRateLimiter:
    """Redis-backed fixed-window edge rate limiter.

    The adapter is intentionally small and synchronous so it can work with the
    simple Redis clients typically used by server bootstrap code. It expects a
    client exposing ``incr`` and optionally ``expire`` and ``ttl``. Redis outage
    handling is explicit: fail-open keeps the public edge available, while
    fail-closed blocks requests with a bounded retry-after value.
    """

    def __init__(
        self,
        *,
        redis_client: Any,
        requests_per_window: int,
        window_seconds: int,
        key_prefix: str = "nexa:edge:rate-limit",
        fail_open: bool = True,
        datastore_span_writer: OtelDatastoreSpanWriter | None = None,
    ) -> None:
        if requests_per_window < 1:
            raise ValueError("requests_per_window must be positive")
        if window_seconds < 1:
            raise ValueError("window_seconds must be positive")
        self.redis_client = redis_client
        self.requests_per_window = int(requests_per_window)
        self.window_seconds = int(window_seconds)
        self.key_prefix = str(key_prefix or "nexa:edge:rate-limit").strip() or "nexa:edge:rate-limit"
        self.fail_open = bool(fail_open)
        self.datastore_span_writer = datastore_span_writer

    def backend_status(self) -> EdgeRateLimitBackendStatus:
        return EdgeRateLimitBackendStatus(
            backend=EDGE_RATE_LIMIT_BACKEND_REDIS,
            available=self.redis_client is not None,
            fail_open=self.fail_open,
            reason=None if self.redis_client is not None else EDGE_RATE_LIMIT_REDIS_UNAVAILABLE_REASON,
        )

    def record(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        if not key:
            return True, 0
        if self.redis_client is None:
            return self._redis_unavailable_result()
        redis_key = redis_rate_limit_key(namespace=self.key_prefix, identity=key, window_seconds=self.window_seconds)
        started_at = time.perf_counter()
        try:
            count = int(self.redis_client.incr(redis_key))
            if count == 1 and hasattr(self.redis_client, "expire"):
                self.redis_client.expire(redis_key, self.window_seconds)
            if count > self.requests_per_window:
                retry_after = self._retry_after(redis_key)
                self._emit_redis_command_span(
                    command="INCR",
                    key=redis_key,
                    started_at=started_at,
                    hit=False,
                    extra={
                        "nexa.rate_limit.allowed": False,
                        "nexa.rate_limit.count": count,
                        "nexa.rate_limit.limit": self.requests_per_window,
                        "nexa.rate_limit.retry_after_s": retry_after,
                    },
                )
                return False, retry_after
            self._emit_redis_command_span(
                command="INCR",
                key=redis_key,
                started_at=started_at,
                hit=True,
                extra={
                    "nexa.rate_limit.allowed": True,
                    "nexa.rate_limit.count": count,
                    "nexa.rate_limit.limit": self.requests_per_window,
                },
            )
            return True, 0
        except Exception as exc:  # noqa: BLE001
            self._emit_redis_command_span(
                command="INCR",
                key=redis_key,
                started_at=started_at,
                hit=None,
                extra={
                    "nexa.rate_limit.outcome": EDGE_RATE_LIMIT_REDIS_ERROR_REASON,
                    "nexa.rate_limit.fail_open": self.fail_open,
                },
                exc=exc,
            )
            return self._redis_unavailable_result()

    def _retry_after(self, redis_key: str) -> int:
        ttl_value = None
        started_at = time.perf_counter()
        if hasattr(self.redis_client, "ttl"):
            try:
                ttl_value = int(self.redis_client.ttl(redis_key))
            except Exception as exc:  # noqa: BLE001
                self._emit_redis_command_span(
                    command="TTL",
                    key=redis_key,
                    started_at=started_at,
                    hit=None,
                    extra={"nexa.rate_limit.outcome": EDGE_RATE_LIMIT_REDIS_ERROR_REASON},
                    exc=exc,
                )
                ttl_value = None
            else:
                self._emit_redis_command_span(
                    command="TTL",
                    key=redis_key,
                    started_at=started_at,
                    hit=None,
                    extra={"nexa.rate_limit.ttl_s": ttl_value},
                )
        if ttl_value is None or ttl_value < 1:
            return max(1, self.window_seconds)
        return ttl_value

    def _redis_unavailable_result(self) -> tuple[bool, int]:
        if self.fail_open:
            return True, 0
        return False, max(1, self.window_seconds)

    def _emit_redis_command_span(
        self,
        *,
        command: str,
        key: str,
        started_at: float,
        hit: bool | None,
        extra: dict[str, Any] | None = None,
        exc: BaseException | None = None,
    ) -> None:
        if self.datastore_span_writer is None:
            return
        duration_ms = max(0, int((time.perf_counter() - started_at) * 1000))
        attributes = build_otel_redis_span_attributes(
            command=command,
            key=key,
            key_prefix=self.key_prefix,
            duration_ms=duration_ms,
            hit=hit,
            extra=extra,
        )
        events = None
        if exc is not None:
            events = [build_otel_datastore_exception_event(exc=exc, attributes=attributes)]
        emit_otel_datastore_span(
            self.datastore_span_writer,
            name="redis.rate_limit.command",
            attributes=attributes,
            events=events,
        )


def build_edge_rate_limiter(
    *,
    backend: str,
    requests_per_window: int,
    window_seconds: int,
    redis_client: Any | None = None,
    redis_key_prefix: str = "nexa:edge:rate-limit",
    redis_fail_open: bool = True,
    in_memory_factory: Any | None = None,
    datastore_span_writer: OtelDatastoreSpanWriter | None = None,
) -> EdgeRateLimiter:
    normalized_backend = normalize_rate_limit_backend(backend)
    if normalized_backend == EDGE_RATE_LIMIT_BACKEND_REDIS:
        return RedisEdgeRateLimiter(
            redis_client=redis_client,
            requests_per_window=requests_per_window,
            window_seconds=window_seconds,
            key_prefix=redis_key_prefix,
            fail_open=redis_fail_open,
            datastore_span_writer=datastore_span_writer,
        )
    if in_memory_factory is None:
        from src.server.edge_security_runtime import InMemoryEdgeRateLimiter

        return InMemoryEdgeRateLimiter(
            requests_per_window=requests_per_window,
            window_seconds=window_seconds,
        )
    return in_memory_factory(
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
    )


__all__ = [
    "EDGE_RATE_LIMIT_BACKEND_MEMORY",
    "EDGE_RATE_LIMIT_BACKEND_REDIS",
    "EDGE_RATE_LIMIT_BACKENDS",
    "EDGE_RATE_LIMIT_REDIS_ERROR_REASON",
    "EDGE_RATE_LIMIT_REDIS_UNAVAILABLE_REASON",
    "EdgeRateLimitBackendStatus",
    "EdgeRateLimiter",
    "RedisEdgeRateLimiter",
    "build_edge_rate_limiter",
    "normalize_rate_limit_backend",
    "redis_rate_limit_key",
]
