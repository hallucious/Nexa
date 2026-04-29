from __future__ import annotations

import pytest

from src.server.edge_rate_limit_runtime import (
    EDGE_RATE_LIMIT_BACKEND_MEMORY,
    EDGE_RATE_LIMIT_BACKEND_REDIS,
    EDGE_RATE_LIMIT_REDIS_UNAVAILABLE_REASON,
    RedisEdgeRateLimiter,
    build_edge_rate_limiter,
    normalize_rate_limit_backend,
    redis_rate_limit_key,
)
from src.server.edge_security_runtime import InMemoryEdgeRateLimiter


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


def test_normalize_rate_limit_backend_accepts_known_backends() -> None:
    assert normalize_rate_limit_backend(None) == EDGE_RATE_LIMIT_BACKEND_MEMORY
    assert normalize_rate_limit_backend("memory") == EDGE_RATE_LIMIT_BACKEND_MEMORY
    assert normalize_rate_limit_backend("REDIS") == EDGE_RATE_LIMIT_BACKEND_REDIS

    with pytest.raises(ValueError, match="Unsupported edge rate limit backend"):
        normalize_rate_limit_backend("memcached")


def test_redis_rate_limit_key_is_namespaced_and_windowed() -> None:
    assert redis_rate_limit_key(namespace="nexa:test", identity="GET:/api/runs:user-1", window_seconds=60) == "nexa:test:60:GET:/api/runs:user-1"


def test_redis_edge_rate_limiter_allows_until_limit_then_blocks_with_ttl() -> None:
    redis = _FakeRedis()
    limiter = RedisEdgeRateLimiter(
        redis_client=redis,
        requests_per_window=2,
        window_seconds=30,
        key_prefix="nexa:test:rate-limit",
    )

    assert limiter.record("POST:/api/runs:user-1") == (True, 0)
    assert limiter.record("POST:/api/runs:user-1") == (True, 0)
    assert limiter.record("POST:/api/runs:user-1") == (False, 30)

    redis_key = "nexa:test:rate-limit:30:POST:/api/runs:user-1"
    assert redis.values[redis_key] == 3
    assert redis.expirations[redis_key] == 30


def test_redis_edge_rate_limiter_fail_open_and_fail_closed_are_explicit() -> None:
    fail_open_limiter = RedisEdgeRateLimiter(
        redis_client=_FailingRedis(),
        requests_per_window=1,
        window_seconds=45,
        fail_open=True,
    )
    assert fail_open_limiter.record("POST:/api/runs:user-1") == (True, 0)

    fail_closed_limiter = RedisEdgeRateLimiter(
        redis_client=_FailingRedis(),
        requests_per_window=1,
        window_seconds=45,
        fail_open=False,
    )
    assert fail_closed_limiter.record("POST:/api/runs:user-1") == (False, 45)


def test_redis_edge_rate_limiter_backend_status_reports_unavailable_without_secrets() -> None:
    limiter = RedisEdgeRateLimiter(
        redis_client=None,
        requests_per_window=1,
        window_seconds=60,
        fail_open=True,
    )

    payload = limiter.backend_status().as_payload()

    assert payload == {
        "backend": EDGE_RATE_LIMIT_BACKEND_REDIS,
        "available": False,
        "fail_open": True,
        "reason": EDGE_RATE_LIMIT_REDIS_UNAVAILABLE_REASON,
    }


def test_build_edge_rate_limiter_creates_memory_or_redis_backend() -> None:
    memory = build_edge_rate_limiter(
        backend="memory",
        requests_per_window=2,
        window_seconds=60,
    )
    redis = build_edge_rate_limiter(
        backend="redis",
        requests_per_window=2,
        window_seconds=60,
        redis_client=_FakeRedis(),
    )

    assert isinstance(memory, InMemoryEdgeRateLimiter)
    assert isinstance(redis, RedisEdgeRateLimiter)
