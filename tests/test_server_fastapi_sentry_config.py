from __future__ import annotations

import pytest

from src.server.fastapi_binding_models import FastApiBindingConfig


def test_fastapi_binding_sentry_config_defaults_to_disabled_safe_noop() -> None:
    config = FastApiBindingConfig()

    assert config.sentry_enabled is False
    assert config.sentry_dsn is None
    assert config.sentry_environment == "local"
    assert config.sentry_release is None
    assert config.sentry_traces_sample_rate == 0.0


def test_fastapi_binding_sentry_config_rejects_invalid_environment() -> None:
    with pytest.raises(ValueError, match="sentry_environment"):
        FastApiBindingConfig(sentry_environment="")


def test_fastapi_binding_sentry_config_rejects_invalid_sample_rate() -> None:
    with pytest.raises(ValueError, match="sentry_traces_sample_rate"):
        FastApiBindingConfig(sentry_traces_sample_rate=1.5)
