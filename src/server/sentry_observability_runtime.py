from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.server.edge_observability_runtime import REDACTED_VALUE, redact_headers, redact_mapping


SENTRY_DISABLED_REASON = "sentry_disabled"
SENTRY_DSN_MISSING_REASON = "sentry_dsn_missing"
SENTRY_SDK_MISSING_REASON = "sentry_sdk_missing"
SENTRY_INITIALIZED_REASON = "sentry_initialized"
SENTRY_INIT_FAILED_REASON = "sentry_init_failed"

REQUEST_BODY_KEYS = {"data", "body", "raw_body", "json", "form", "files"}
REQUEST_COOKIE_KEYS = {"cookies", "cookie"}
USER_PII_KEYS = {"email", "ip_address", "username", "name", "id"}


@dataclass(frozen=True)
class SentryInitializationResult:
    enabled: bool
    initialized: bool
    reason: str
    dsn_configured: bool
    environment: str
    sample_rate: float

    def as_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "initialized": self.initialized,
            "reason": self.reason,
            "dsn_configured": self.dsn_configured,
            "environment": self.environment,
            "sample_rate": self.sample_rate,
        }


def _redact_text(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    lowered = text.lower()
    if "sk-" in lowered or "bearer " in lowered or "secret" in lowered or "token" in lowered:
        return REDACTED_VALUE
    if len(text) > 240:
        return text[:237] + "..."
    return text


def _scrub_collection(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _scrub_mapping(value)
    if isinstance(value, list):
        return [_scrub_collection(item) for item in value]
    if isinstance(value, tuple):
        return [_scrub_collection(item) for item in value]
    return _redact_text(value)


def _scrub_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    scrubbed: dict[str, Any] = {}
    for key, value in mapping.items():
        key_text = str(key)
        normalized = key_text.strip().lower().replace("-", "_")
        if normalized in REQUEST_BODY_KEYS or normalized in REQUEST_COOKIE_KEYS:
            scrubbed[key_text] = REDACTED_VALUE
        elif normalized in USER_PII_KEYS:
            scrubbed[key_text] = REDACTED_VALUE
        elif isinstance(value, Mapping):
            scrubbed[key_text] = _scrub_mapping(value)
        elif isinstance(value, (list, tuple)):
            scrubbed[key_text] = [_scrub_collection(item) for item in value]
        else:
            scrubbed[key_text] = _redact_text(value)
    return redact_mapping(scrubbed)


def scrub_sentry_event(event: Mapping[str, Any] | None, hint: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Return a privacy-safe Sentry event payload.

    This function is intended for Sentry ``before_send``. It is deliberately
    usable without the Sentry SDK so that redaction can be tested directly.
    """

    if not isinstance(event, Mapping):
        return None

    scrubbed = _scrub_mapping(event)

    request = scrubbed.get("request")
    if isinstance(request, Mapping):
        request_dict = dict(request)
        headers = request_dict.get("headers")
        request_dict["headers"] = redact_headers(headers if isinstance(headers, Mapping) else {})
        for key in REQUEST_BODY_KEYS | REQUEST_COOKIE_KEYS:
            if key in request_dict:
                request_dict[key] = REDACTED_VALUE
        if "query_string" in request_dict:
            request_dict["query_string"] = REDACTED_VALUE
        scrubbed["request"] = request_dict

    user = scrubbed.get("user")
    if isinstance(user, Mapping):
        user_dict = dict(user)
        for key in USER_PII_KEYS:
            if key in user_dict:
                user_dict[key] = REDACTED_VALUE
        scrubbed["user"] = user_dict

    return scrubbed


def initialize_sentry_observability(
    *,
    enabled: bool,
    dsn: str | None,
    environment: str,
    release: str | None = None,
    traces_sample_rate: float = 0.0,
    sdk_module: Any | None = None,
) -> SentryInitializationResult:
    """Initialize Sentry when explicitly configured.

    The function avoids a hard dependency on ``sentry_sdk``. If the SDK is not
    installed, it returns a structured no-op result instead of failing app boot.
    """

    env = str(environment or "").strip() or "local"
    sample_rate = float(traces_sample_rate)
    dsn_configured = bool(str(dsn or "").strip())

    if not enabled:
        return SentryInitializationResult(
            enabled=False,
            initialized=False,
            reason=SENTRY_DISABLED_REASON,
            dsn_configured=dsn_configured,
            environment=env,
            sample_rate=sample_rate,
        )
    if not dsn_configured:
        return SentryInitializationResult(
            enabled=True,
            initialized=False,
            reason=SENTRY_DSN_MISSING_REASON,
            dsn_configured=False,
            environment=env,
            sample_rate=sample_rate,
        )

    sdk = sdk_module
    if sdk is None:
        try:
            import sentry_sdk as sdk  # type: ignore[no-redef]
        except Exception:
            return SentryInitializationResult(
                enabled=True,
                initialized=False,
                reason=SENTRY_SDK_MISSING_REASON,
                dsn_configured=True,
                environment=env,
                sample_rate=sample_rate,
            )

    try:
        sdk.init(
            dsn=dsn,
            environment=env,
            release=release,
            traces_sample_rate=sample_rate,
            send_default_pii=False,
            before_send=scrub_sentry_event,
        )
    except Exception:
        return SentryInitializationResult(
            enabled=True,
            initialized=False,
            reason=SENTRY_INIT_FAILED_REASON,
            dsn_configured=True,
            environment=env,
            sample_rate=sample_rate,
        )

    return SentryInitializationResult(
        enabled=True,
        initialized=True,
        reason=SENTRY_INITIALIZED_REASON,
        dsn_configured=True,
        environment=env,
        sample_rate=sample_rate,
    )


__all__ = [
    "SENTRY_DISABLED_REASON",
    "SENTRY_DSN_MISSING_REASON",
    "SENTRY_INIT_FAILED_REASON",
    "SENTRY_INITIALIZED_REASON",
    "SENTRY_SDK_MISSING_REASON",
    "SentryInitializationResult",
    "initialize_sentry_observability",
    "scrub_sentry_event",
]
