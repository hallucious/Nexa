from __future__ import annotations

from src.server.edge_security_runtime import InMemoryEdgeRateLimiter, apply_security_headers, cors_headers, security_headers


def test_edge_security_headers_include_public_browser_baseline() -> None:
    headers = security_headers()

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_apply_security_headers_preserves_existing_values() -> None:
    headers = {"x-frame-options": "SAMEORIGIN"}

    apply_security_headers(headers)

    assert headers["x-frame-options"] == "SAMEORIGIN"
    assert headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert headers["x-content-type-options"] == "nosniff"


def test_edge_cors_rejects_wildcard_like_unlisted_origins() -> None:
    headers = cors_headers(
        origin="https://evil.example",
        allowed_origins=("https://app.nexa.example",),
        allowed_methods=("GET", "POST"),
        allowed_headers=("content-type",),
        max_age_seconds=600,
    )

    assert headers == {}


def test_edge_rate_limiter_uses_deterministic_window_accounting() -> None:
    limiter = InMemoryEdgeRateLimiter(requests_per_window=2, window_seconds=10)

    assert limiter.record("POST:/api/runs:user-owner", now=100.0) == (True, 0)
    assert limiter.record("POST:/api/runs:user-owner", now=101.0) == (True, 0)
    assert limiter.record("POST:/api/runs:user-owner", now=102.0) == (False, 8)
    assert limiter.record("POST:/api/runs:user-owner", now=111.0) == (True, 0)
