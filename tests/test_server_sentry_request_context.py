from __future__ import annotations

import json

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.sentry_observability_runtime import build_sentry_request_context


def test_build_sentry_request_context_scrubs_http_request_boundary() -> None:
    context = build_sentry_request_context(
        method="post",
        path="/api/runs",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Forwarded-For": "203.0.113.9",
        },
        query_params={
            "api_key": "sk-query-secret",
            "safe": "value",
        },
        request_id="req-001",
        session_claims={
            "sub": "user-owner",
            "session_token": "sk-session-secret",
            "roles": ["editor"],
        },
        status_code=500,
        extra={
            "worker_token": "sk-worker-secret",
            "safe_count": 3,
        },
    )

    serialized = json.dumps(context, sort_keys=True)
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-session-secret" not in serialized
    assert "sk-worker-secret" not in serialized
    assert "203.0.113.9" not in serialized
    assert context["request"]["method"] == "POST"
    assert context["request"]["path"] == "/api/runs"
    assert context["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert context["request"]["headers"]["cookie"] == REDACTED_VALUE
    assert context["request"]["headers"]["user-agent"] == "pytest-client"
    assert "x-forwarded-for" not in context["request"]["headers"]
    assert context["request"]["query_params"]["api_key"] == REDACTED_VALUE
    assert context["request"]["query_params"]["safe"] == "value"
    assert context["request_id"] == "req-001"
    assert context["status_code"] == 500
    assert context["session"]["session_token"] == REDACTED_VALUE
    assert context["worker_token"] == REDACTED_VALUE
    assert context["safe_count"] == 3
