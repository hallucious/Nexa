from __future__ import annotations

from types import SimpleNamespace

from src.server.fastapi_app_bootstrap import install_fastapi_app_observability_bootstrap
from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.sentry_observability_runtime import read_sentry_observability_app_state


class _FakeApp:
    def __init__(self) -> None:
        self.state = SimpleNamespace()
        self.middleware = []

    def middleware(self, _kind):
        def _decorator(func):
            self.middleware.append(func)
            return func
        return _decorator


def test_fastapi_app_observability_bootstrap_disabled_is_safe_noop_state() -> None:
    app = SimpleNamespace(state=SimpleNamespace())

    install_fastapi_app_observability_bootstrap(app, FastApiBindingConfig())

    state = read_sentry_observability_app_state(app)
    assert state["enabled"] is False
    assert state["initialized"] is False
    assert "dsn" not in state


def test_fastapi_app_observability_bootstrap_suppresses_setup_failures() -> None:
    class _NoStateApp:
        @property
        def state(self):
            raise RuntimeError("state unavailable")

    install_fastapi_app_observability_bootstrap(_NoStateApp(), FastApiBindingConfig())
