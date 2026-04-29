from __future__ import annotations

import json

from src.server.edge_security_runtime import (
    SENSITIVE_DENIAL_REASON,
    apply_security_headers,
    cors_headers,
    path_is_rate_limited,
    rate_limited_payload,
    security_headers,
)
from src.server.fastapi_binding_models import FastApiBindingConfig


def test_cors_preflight_requires_allowed_origin_method_and_headers() -> None:
    headers = cors_headers(
        origin="https://app.nexa.example/",
        allowed_origins=("https://app.nexa.example",),
        allowed_methods=("GET", "POST", "OPTIONS"),
        allowed_headers=("content-type", "x-nexa-session-claims"),
        max_age_seconds=600,
        requested_method="post",
        requested_headers="Content-Type, X-Nexa-Session-Claims",
    )

    assert headers["access-control-allow-origin"] == "https://app.nexa.example"
    assert headers["access-control-allow-methods"] == "GET, POST, OPTIONS"
    assert headers["access-control-allow-headers"] == "content-type, x-nexa-session-claims"
    assert headers["access-control-max-age"] == "600"
    assert headers["vary"] == "Origin"


def test_cors_preflight_rejects_unlisted_method_even_when_origin_is_allowed() -> None:
    headers = cors_headers(
        origin="https://app.nexa.example",
        allowed_origins=("https://app.nexa.example",),
        allowed_methods=("GET", "POST", "OPTIONS"),
        allowed_headers=("content-type", "x-nexa-session-claims"),
        max_age_seconds=600,
        requested_method="DELETE",
        requested_headers="content-type",
    )

    assert headers == {}


def test_cors_preflight_rejects_unlisted_headers_even_when_origin_is_allowed() -> None:
    headers = cors_headers(
        origin="https://app.nexa.example",
        allowed_origins=("https://app.nexa.example",),
        allowed_methods=("GET", "POST", "OPTIONS"),
        allowed_headers=("content-type", "x-nexa-session-claims"),
        max_age_seconds=600,
        requested_method="POST",
        requested_headers="content-type, authorization, x-unsafe-debug-token",
    )

    assert headers == {}


def test_actual_cors_response_still_allows_origin_without_preflight_request_fields() -> None:
    headers = cors_headers(
        origin="https://app.nexa.example",
        allowed_origins=("https://app.nexa.example",),
        allowed_methods=("GET", "POST", "OPTIONS"),
        allowed_headers=("content-type", "x-nexa-session-claims"),
        max_age_seconds=600,
    )

    assert headers["access-control-allow-origin"] == "https://app.nexa.example"


def test_default_public_sensitive_paths_are_rate_limited() -> None:
    config = FastApiBindingConfig(rate_limit_enabled=True)

    assert path_is_rate_limited("/api/runs", config.rate_limit_path_prefixes) is True
    assert path_is_rate_limited("/api/runs/run-001", config.rate_limit_path_prefixes) is True
    assert path_is_rate_limited("/api/workspaces/ws-001/uploads", config.rate_limit_path_prefixes) is True
    assert path_is_rate_limited("/api/workspaces/ws-001/uploads/upload-001", config.rate_limit_path_prefixes) is True
    assert path_is_rate_limited("/api/workspaces/ws-001/result-history", config.rate_limit_path_prefixes) is False


def test_rate_limited_payload_contains_only_safe_denial_fields() -> None:
    payload = rate_limited_payload()
    serialized = json.dumps(payload, sort_keys=True)

    assert payload == {"status": "rate_limited", "reason": SENSITIVE_DENIAL_REASON}
    assert "request_body" not in serialized
    assert "raw_body" not in serialized
    assert "authorization" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_security_headers_include_public_edge_baseline_and_do_not_overwrite_existing_values() -> None:
    expected = security_headers()
    headers = {"x-frame-options": "SAMEORIGIN"}

    apply_security_headers(headers)

    assert headers["x-frame-options"] == "SAMEORIGIN"
    assert headers["x-content-type-options"] == expected["x-content-type-options"]
    assert headers["strict-transport-security"] == expected["strict-transport-security"]
    assert headers["content-security-policy"] == expected["content-security-policy"]
    assert headers["permissions-policy"] == expected["permissions-policy"]
