from __future__ import annotations

import inspect
from typing import Any, Callable


_AUTOWIRE_INSTALLED = False
_ORIGINAL_FASTAPI_INIT: Any | None = None
_APP_AUTOWIRE_STATE_KEY = "_nexa_fastapi_sentry_autowired"


def _looks_like_sentry_config(config: Any) -> bool:
    return config is not None and all(
        hasattr(config, name)
        for name in (
            "sentry_enabled",
            "sentry_dsn",
            "sentry_environment",
            "sentry_release",
            "sentry_traces_sample_rate",
        )
    )


def _resolve_fastapi_binding_context_from_stack() -> tuple[Any | None, Callable[..., Any] | None]:
    frame = inspect.currentframe()
    if frame is None:
        return None, None
    try:
        current = frame.f_back
        while current is not None:
            owner = current.f_locals.get("self")
            config = getattr(owner, "config", None)
            if _looks_like_sentry_config(config):
                dependencies = getattr(owner, "dependencies", None)
                resolver = getattr(dependencies, "session_claims_resolver", None)
                return config, resolver if callable(resolver) else None
            current = current.f_back
    finally:
        del frame
    return None, None


def install_fastapi_sentry_autowire() -> bool:
    """Install a narrow FastAPI constructor hook for Nexa's route binding.

    The hook is intentionally conservative: it only activates when a FastAPI app
    is being constructed from a call stack that exposes a FastApiRouteBindings
    instance with a Sentry-capable config object, and it only installs the
    middleware when that config explicitly enables Sentry.
    """

    global _AUTOWIRE_INSTALLED, _ORIGINAL_FASTAPI_INIT
    if _AUTOWIRE_INSTALLED:
        return True
    try:
        from fastapi import FastAPI
    except Exception:
        return False

    original_init = FastAPI.__init__
    _ORIGINAL_FASTAPI_INIT = original_init

    def _nexa_fastapi_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        original_init(self, *args, **kwargs)
        state = getattr(self, "state", None)
        if state is not None and bool(getattr(state, _APP_AUTOWIRE_STATE_KEY, False)):
            return
        config, session_claims_resolver = _resolve_fastapi_binding_context_from_stack()
        if not _looks_like_sentry_config(config) or not bool(getattr(config, "sentry_enabled", False)):
            return
        try:
            from src.server.fastapi_sentry_binding import install_fastapi_sentry_exception_middleware

            install_fastapi_sentry_exception_middleware(
                self,
                config,
                session_claims_resolver=session_claims_resolver,
            )
            state = getattr(self, "state", None)
            if state is not None:
                setattr(state, _APP_AUTOWIRE_STATE_KEY, True)
        except Exception:
            # Observability bootstrap must never break FastAPI app construction.
            return

    FastAPI.__init__ = _nexa_fastapi_init  # type: ignore[method-assign]
    _AUTOWIRE_INSTALLED = True
    return True


__all__ = ["install_fastapi_sentry_autowire"]
