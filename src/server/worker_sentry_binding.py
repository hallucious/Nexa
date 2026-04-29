from __future__ import annotations

from typing import Any, Mapping

from src.server.sentry_observability_runtime import (
    SentryCaptureResult,
    build_sentry_exception_event,
    capture_sentry_exception,
)


WORKER_SENTRY_FAILURE_REASON = "worker_exception_captured"


def _config_sentry_enabled(config: Any | None) -> bool:
    return bool(getattr(config, "sentry_enabled", False)) if config is not None else False


def worker_sentry_enabled(ctx: Mapping[str, Any] | None) -> bool:
    """Resolve whether worker-side Sentry capture is enabled.

    Workers do not have a FastAPI app object. They receive operational runtime
    objects through arq ``ctx`` instead, so this adapter accepts either a direct
    ``sentry_enabled`` flag or a config-like object under ``sentry_config`` or
    ``config``. Missing configuration is a safe no-op.
    """

    if not isinstance(ctx, Mapping):
        return False
    if "sentry_enabled" in ctx:
        return bool(ctx.get("sentry_enabled"))
    return _config_sentry_enabled(ctx.get("sentry_config")) or _config_sentry_enabled(ctx.get("config"))


def build_worker_sentry_exception_context(
    *,
    job_payload: Mapping[str, Any] | None = None,
    stage: str,
    failure_reason: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a privacy-safe worker exception context.

    The context intentionally keeps stable run identifiers while relying on the
    shared Sentry scrubber to redact sensitive fields such as tokens, API keys,
    credentials, request bodies, and raw exception/secret text before SDK capture.
    """

    payload = dict(job_payload or {})
    context: dict[str, Any] = {
        "worker": {
            "stage": str(stage or "unknown"),
            "run_id": str(payload.get("run_id") or ""),
            "workspace_id": str(payload.get("workspace_id") or ""),
            "run_request_id": str(payload.get("run_request_id") or ""),
            "target_type": str(payload.get("target_type") or ""),
            "target_ref": str(payload.get("target_ref") or ""),
            "provider_id": payload.get("provider_id"),
            "model_id": payload.get("model_id"),
            "mode": str(payload.get("mode") or "standard"),
        },
        "job_payload": payload,
    }
    if failure_reason:
        context["failure_reason"] = str(failure_reason)
    if isinstance(extra, Mapping):
        context.update(dict(extra))
    return context


def build_worker_sentry_exception_event(
    *,
    exc: BaseException,
    job_payload: Mapping[str, Any] | None = None,
    stage: str,
    failure_reason: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build the exact scrubbed Sentry event used for worker failures."""

    return build_sentry_exception_event(
        exc=exc,
        context=build_worker_sentry_exception_context(
            job_payload=job_payload,
            stage=stage,
            failure_reason=failure_reason,
            extra=extra,
        ),
    )


def capture_worker_sentry_exception(
    *,
    ctx: Mapping[str, Any] | None,
    exc: BaseException,
    job_payload: Mapping[str, Any] | None = None,
    stage: str,
    failure_reason: str | None = None,
    extra: Mapping[str, Any] | None = None,
    sdk_module: Any | None = None,
) -> SentryCaptureResult:
    """Capture a worker exception through Sentry without leaking job payloads.

    This helper is safe for arq worker functions: it has no hard SDK dependency,
    never raises to callers, and uses the shared Sentry scrubber before the event
    reaches the SDK boundary.
    """

    resolved_sdk = sdk_module
    if resolved_sdk is None and isinstance(ctx, Mapping):
        resolved_sdk = ctx.get("sentry_sdk")
    return capture_sentry_exception(
        exc=exc,
        enabled=worker_sentry_enabled(ctx),
        context=build_worker_sentry_exception_context(
            job_payload=job_payload,
            stage=stage,
            failure_reason=failure_reason,
            extra=extra,
        ),
        sdk_module=resolved_sdk,
    )


__all__ = [
    "WORKER_SENTRY_FAILURE_REASON",
    "build_worker_sentry_exception_context",
    "build_worker_sentry_exception_event",
    "capture_worker_sentry_exception",
    "worker_sentry_enabled",
]
