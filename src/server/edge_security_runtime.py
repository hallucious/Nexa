from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import time
from typing import Any, Mapping


SECURITY_HEADERS: dict[str, str] = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
    "content-security-policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
}


SENSITIVE_DENIAL_REASON = "edge_rate_limit_exceeded"


@dataclass
class InMemoryEdgeRateLimiter:
    """Small process-local rate limiter for Phase 2G edge-hardening smoke coverage.

    This is not the long-term Redis-backed limiter from the SaaS plan.
    It gives the FastAPI edge a real enforceable boundary while keeping the
    implementation dependency-free for the current skeleton phase.
    """

    requests_per_window: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.requests_per_window < 1:
            raise ValueError("requests_per_window must be positive")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be positive")
        self._buckets: dict[str, tuple[float, int]] = {}

    def record(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        if not key:
            return True, self.requests_per_window
        now_value = time.monotonic() if now is None else float(now)
        window_started_at, count = self._buckets.get(key, (now_value, 0))
        if now_value - window_started_at >= self.window_seconds:
            window_started_at, count = now_value, 0
        if count >= self.requests_per_window:
            retry_after = max(1, int(self.window_seconds - (now_value - window_started_at)))
            self._buckets[key] = (window_started_at, count)
            return False, retry_after
        self._buckets[key] = (window_started_at, count + 1)
        return True, 0


def security_headers() -> dict[str, str]:
    return dict(SECURITY_HEADERS)


def apply_security_headers(headers: Any) -> None:
    for key, value in SECURITY_HEADERS.items():
        if key not in headers:
            headers[key] = value


def normalize_origin(origin: str | None) -> str | None:
    normalized = str(origin or "").strip()
    if not normalized:
        return None
    return normalized.rstrip("/")


def origin_allowed(origin: str | None, allowed_origins: tuple[str, ...]) -> bool:
    normalized = normalize_origin(origin)
    if normalized is None:
        return False
    return normalized in {normalize_origin(item) for item in allowed_origins if normalize_origin(item)}


def _normalize_cors_token(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_cors_method(value: Any) -> str:
    return str(value or "").strip().upper()


def _parse_requested_headers(value: str | tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    return tuple(item for item in (_normalize_cors_token(raw) for raw in raw_items) if item)


def _requested_method_allowed(requested_method: str | None, allowed_methods: tuple[str, ...]) -> bool:
    normalized_request = _normalize_cors_method(requested_method)
    if not normalized_request:
        return True
    allowed = {_normalize_cors_method(item) for item in allowed_methods if _normalize_cors_method(item)}
    return "*" in allowed or normalized_request in allowed


def _requested_headers_allowed(
    requested_headers: str | tuple[str, ...] | list[str] | None,
    allowed_headers: tuple[str, ...],
) -> bool:
    requested = set(_parse_requested_headers(requested_headers))
    if not requested:
        return True
    allowed = {_normalize_cors_token(item) for item in allowed_headers if _normalize_cors_token(item)}
    return "*" in allowed or requested.issubset(allowed)


def cors_headers(
    *,
    origin: str | None,
    allowed_origins: tuple[str, ...],
    allowed_methods: tuple[str, ...],
    allowed_headers: tuple[str, ...],
    max_age_seconds: int,
    requested_method: str | None = None,
    requested_headers: str | tuple[str, ...] | list[str] | None = None,
) -> dict[str, str]:
    if not origin_allowed(origin, allowed_origins):
        return {}
    if not _requested_method_allowed(requested_method, allowed_methods):
        return {}
    if not _requested_headers_allowed(requested_headers, allowed_headers):
        return {}
    return {
        "access-control-allow-origin": normalize_origin(origin) or "",
        "access-control-allow-methods": ", ".join(allowed_methods),
        "access-control-allow-headers": ", ".join(allowed_headers),
        "access-control-max-age": str(max_age_seconds),
        "vary": "Origin",
    }


def is_cors_preflight(*, method: str, headers: Mapping[str, Any]) -> bool:
    return method.upper() == "OPTIONS" and bool(headers.get("access-control-request-method"))


def path_is_rate_limited(path: str, prefixes: tuple[str, ...]) -> bool:
    normalized_path = str(path or "")
    for raw_prefix in prefixes:
        prefix = str(raw_prefix or "").strip()
        if not prefix:
            continue
        if "*" in prefix:
            if fnmatch.fnmatch(normalized_path, prefix) or fnmatch.fnmatch(normalized_path, prefix.rstrip("/") + "/*"):
                return True
            continue
        if normalized_path == prefix or normalized_path.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def rate_limit_identity(
    *,
    method: str,
    path: str,
    client_host: str | None,
    session_claims: Mapping[str, Any] | None,
) -> str:
    user_ref = None
    if isinstance(session_claims, Mapping):
        user_ref = session_claims.get("user_id") or session_claims.get("sub") or session_claims.get("subject")
    actor = str(user_ref or client_host or "anonymous").strip() or "anonymous"
    return f"{str(method or '').upper()}:{path}:{actor}"


def rate_limited_payload() -> dict[str, str]:
    """Return a denial body that intentionally excludes request payload data."""

    return {
        "status": "rate_limited",
        "reason": SENSITIVE_DENIAL_REASON,
    }


__all__ = [
    "InMemoryEdgeRateLimiter",
    "SENSITIVE_DENIAL_REASON",
    "apply_security_headers",
    "cors_headers",
    "is_cors_preflight",
    "origin_allowed",
    "path_is_rate_limited",
    "rate_limit_identity",
    "rate_limited_payload",
    "security_headers",
]
