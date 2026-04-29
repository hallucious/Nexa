from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.edge_rate_limit_runtime import EDGE_RATE_LIMIT_BACKEND_REDIS
from src.server.edge_security_runtime import path_is_rate_limited


class _FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = int(seconds)

    def ttl(self, key: str) -> int:
        return self.expirations.get(key, 60)


class _FailingRedis:
    def incr(self, key: str) -> int:
        raise RuntimeError("redis unavailable with sk-secret")


def test_fastapi_binding_config_exposes_redis_rate_limit_defaults() -> None:
    config = FastApiBindingConfig()

    assert config.rate_limit_backend == "memory"
    assert config.rate_limit_redis_key_prefix == "nexa:edge:rate-limit"
    assert config.rate_limit_redis_fail_open is True
    assert "/api/runs" in config.rate_limit_path_prefixes
    assert "/api/workspaces/*/uploads" in config.rate_limit_path_prefixes


def test_fastapi_binding_config_rejects_invalid_rate_limit_backend() -> None:
    with pytest.raises(ValueError, match="rate_limit_backend"):
        FastApiBindingConfig(rate_limit_backend="memcached")


def test_path_is_rate_limited_supports_upload_wildcard_prefix() -> None:
    prefixes = ("/api/runs", "/api/workspaces/*/uploads")

    assert path_is_rate_limited("/api/runs", prefixes) is True
    assert path_is_rate_limited("/api/runs/run-001", prefixes) is True
    assert path_is_rate_limited("/api/workspaces/ws-001/uploads/presign", prefixes) is True
    assert path_is_rate_limited("/api/workspaces/ws-001/uploads/upload-001/confirm", prefixes) is True
    assert path_is_rate_limited("/api/workspaces/ws-001/library", prefixes) is False


def test_create_fastapi_app_uses_redis_rate_limit_backend_for_upload_paths() -> None:
    fake_redis = _FakeRedis()
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(edge_rate_limit_redis_client_provider=lambda: fake_redis),
        config=FastApiBindingConfig(
            rate_limit_enabled=True,
            rate_limit_backend=EDGE_RATE_LIMIT_BACKEND_REDIS,
            rate_limit_requests_per_window=1,
            rate_limit_window_seconds=60,
            rate_limit_redis_key_prefix="nexa:test:edge-rate-limit",
        ),
    )
    client = TestClient(app, raise_server_exceptions=False)

    first = client.post(
        "/api/workspaces/ws-redis/uploads/presign",
        headers={"x-nexa-request-id": "req-redis-rate-001"},
        json={"filename": "contract.pdf", "content_type": "application/pdf", "size_bytes": 10},
    )
    second = client.post(
        "/api/workspaces/ws-redis/uploads/presign",
        headers={"x-nexa-request-id": "req-redis-rate-002"},
        json={"filename": "contract.pdf", "content_type": "application/pdf", "size_bytes": 10},
    )

    assert first.status_code != 429
    assert second.status_code == 429
    payload = second.json()
    assert payload == {"status": "rate_limited", "reason": "edge_rate_limit_exceeded"}
    assert second.headers["x-nexa-request-id"] == "req-redis-rate-002"
    assert second.headers["retry-after"] == "60"
    assert any(key.startswith("nexa:test:edge-rate-limit:60:") for key in fake_redis.counts)
    serialized_keys = json.dumps(sorted(fake_redis.counts), sort_keys=True)
    assert "contract.pdf" not in serialized_keys


def test_create_fastapi_app_redis_rate_limit_fail_closed_blocks_without_leaking_redis_error() -> None:
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(edge_rate_limit_redis_client_provider=lambda: _FailingRedis()),
        config=FastApiBindingConfig(
            rate_limit_enabled=True,
            rate_limit_backend=EDGE_RATE_LIMIT_BACKEND_REDIS,
            rate_limit_requests_per_window=1,
            rate_limit_window_seconds=30,
            rate_limit_redis_fail_open=False,
        ),
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/runs",
        headers={"x-nexa-request-id": "req-redis-fail-closed"},
        json={"workspace_id": "ws-001", "api_key": "sk-request-secret"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    response_text = response.text
    assert "redis unavailable" not in response_text
    assert "sk-request-secret" not in response_text
    assert response.json() == {"status": "rate_limited", "reason": "edge_rate_limit_exceeded"}
