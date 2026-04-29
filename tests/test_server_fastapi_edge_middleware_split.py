from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.edge_rate_limit_runtime import EDGE_RATE_LIMIT_BACKEND_MEMORY
from src.server.fastapi_edge_middleware import register_fastapi_edge_middleware


class _FakeSentrySdkModule:
    def __init__(self) -> None:
        self.init_kwargs = None
        self.captured_events: list[dict] = []

    def init(self, **kwargs):
        self.init_kwargs = dict(kwargs)

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "split-edge-event-001"


def test_fastapi_binding_build_app_uses_split_edge_middleware() -> None:
    # This test locks the refactor boundary: build_app delegates edge behavior
    # to the extracted middleware module instead of owning the full middleware body.
    from src.server.fastapi_binding import FastApiRouteBindings

    names = set(FastApiRouteBindings.build_app.__code__.co_names)
    assert "register_fastapi_edge_middleware" in names
    assert "build_router" in names


def test_split_edge_middleware_preserves_exception_payload_and_sentry_side_channel(monkeypatch) -> None:
    fake_sdk = _FakeSentrySdkModule()
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(
            session_claims_resolver=lambda _request: {"sub": "raw-user-id", "session_token": "sk-session-secret"},
        ),
        config=FastApiBindingConfig(
            sentry_enabled=True,
            sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            sentry_environment="production",
        ),
    )

    @app.get("/split-edge-boom")
    async def _split_edge_boom():
        raise RuntimeError("split edge handler failed with sk-runtime-secret")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/split-edge-boom?api_key=sk-query-secret",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Nexa-Request-Id": "req-split-edge-001",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "status": "error",
        "reason": "edge_exception_captured",
        "request_id": "req-split-edge-001",
    }
    assert "sk-runtime-secret" not in response.text
    assert "sk-header-secret" not in response.text
    assert "sk-query-secret" not in response.text

    assert len(fake_sdk.captured_events) == 1
    event = fake_sdk.captured_events[0]
    serialized = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-session-secret" not in serialized
    assert event["extra"]["request_id"] == "req-split-edge-001"
    assert event["extra"]["request"]["headers"]["authorization"] == "<redacted>"
    assert event["extra"]["request"]["headers"]["cookie"] == "<redacted>"
    assert event["extra"]["session"]["session_token"] == "<redacted>"


def test_split_edge_middleware_keeps_memory_rate_limit_backend_default() -> None:
    events: list[dict] = []
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(edge_observation_writer=events.append),
        config=FastApiBindingConfig(
            rate_limit_enabled=True,
            rate_limit_backend=EDGE_RATE_LIMIT_BACKEND_MEMORY,
            rate_limit_requests_per_window=1,
            rate_limit_window_seconds=60,
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    first = client.get("/api/runs/run-rate-limited", headers={"X-Nexa-Request-Id": "req-rate-1"})
    second = client.get("/api/runs/run-rate-limited", headers={"X-Nexa-Request-Id": "req-rate-2"})

    assert first.status_code in {401, 404, 405}
    assert second.status_code == 429
    assert second.json()["reason"] == "edge_rate_limit_exceeded"
    assert "req-rate-2" == second.headers["x-nexa-request-id"]
