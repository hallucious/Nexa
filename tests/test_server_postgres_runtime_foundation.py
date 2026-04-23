from __future__ import annotations

import asyncio

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.server.database_models import PostgresConnectionSettings
from src.server.dependency_factory import build_default_readiness_checks
from src.server.health_routes import ReadinessChecks
from src.server.pg.engine import (
    build_asyncpg_connection_url,
    build_psycopg_connection_url,
    get_postgres_engine,
    get_postgres_sync_engine,
    reset_postgres_engine_cache,
    resolve_database_password,
)
from src.server.pg.readiness import (
    build_postgres_readiness_checks,
    check_alembic_head_alignment,
    check_provider_bootstrap_posture,
)


def test_build_asyncpg_connection_url_uses_asyncpg_driver_and_password_redaction() -> None:
    settings = PostgresConnectionSettings(
        host="db.internal",
        port=5432,
        database_name="nexa_prod",
        username="nexa_service",
    )

    url = build_asyncpg_connection_url(settings, password="secret")
    redacted = build_asyncpg_connection_url(settings, password="secret", redact_password=True)

    assert url.startswith("postgresql+asyncpg://nexa_service:secret@db.internal:5432/nexa_prod?")
    assert "%2A%2A%2A" in redacted


def test_resolve_database_password_uses_named_password_env_var() -> None:
    settings = PostgresConnectionSettings(
        host="localhost",
        port=5432,
        database_name="nexa",
        username="nexa",
        password_env_var="SERVER_DB_PASSWORD",
    )

    assert resolve_database_password(settings, env={"SERVER_DB_PASSWORD": "pw-123"}) == "pw-123"


def test_get_postgres_engine_reuses_cached_engine_for_same_redacted_url(monkeypatch) -> None:
    env = {
        "NEXA_SERVER_DB_HOST": "db.internal",
        "NEXA_SERVER_DB_PORT": "5432",
        "NEXA_SERVER_DB_NAME": "nexa",
        "NEXA_SERVER_DB_USER": "nexa",
        "NEXA_SERVER_DB_PASSWORD": "secret",
    }
    created = []

    def _fake_create(settings, *, password):
        engine = object()
        created.append((settings, password, engine))
        return engine

    monkeypatch.setattr("src.server.pg.engine.create_async_engine_from_settings", _fake_create)
    reset_postgres_engine_cache()
    try:
        engine_a = get_postgres_engine(env)
        engine_b = get_postgres_engine(env)
        assert engine_a is engine_b
        assert len(created) == 1
    finally:
        reset_postgres_engine_cache()


def test_check_alembic_head_alignment_reports_matching_and_out_of_date_states(monkeypatch, tmp_path: Path) -> None:
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = alembic\n")
    script_location = tmp_path / "alembic"
    script_location.mkdir()
    class DummyAsyncEngine:
        url = "postgresql+asyncpg://nexa:secret@localhost:5432/nexa"

    engine = DummyAsyncEngine()

    class DummyConfig:
        def __init__(self, path: str) -> None:
            self.path = path
            self.options: dict[str, str] = {}

        def set_main_option(self, key: str, value: str) -> None:
            self.options[key] = value

    class DummyScriptDirectory:
        def get_heads(self) -> tuple[str, ...]:
            return ("rev_0001",)

    class DummyScriptLoader:
        @staticmethod
        def from_config(config):
            return DummyScriptDirectory()

    monkeypatch.setattr("src.server.pg.readiness.Config", DummyConfig)
    monkeypatch.setattr("src.server.pg.readiness.ScriptDirectory", DummyScriptLoader)
    async def _matching_heads(engine):
        return ("rev_0001",)

    monkeypatch.setattr(
        "src.server.pg.readiness._current_heads",
        _matching_heads,
    )

    matching = asyncio.run(check_alembic_head_alignment(
        engine,
        alembic_ini_path=alembic_ini,
        script_location=script_location,
    ))
    assert matching["ready"] is True
    assert matching["status"] == "ok"

    async def _outdated_heads(engine):
        return ("rev_0000",)

    monkeypatch.setattr(
        "src.server.pg.readiness._current_heads",
        _outdated_heads,
    )
    out_of_date = asyncio.run(check_alembic_head_alignment(
        engine,
        alembic_ini_path=alembic_ini,
        script_location=script_location,
    ))
    assert out_of_date["ready"] is False
    assert out_of_date["status"] == "out_of_date"




def test_build_psycopg_connection_url_uses_sync_driver_and_password_redaction() -> None:
    settings = PostgresConnectionSettings(
        host="db.internal",
        port=5432,
        database_name="nexa_prod",
        username="nexa_service",
    )

    url = build_psycopg_connection_url(settings, password="secret")
    redacted = build_psycopg_connection_url(settings, password="secret", redact_password=True)

    assert url.startswith("postgresql+psycopg://nexa_service:secret@db.internal:5432/nexa_prod?")
    assert "%2A%2A%2A" in redacted


def test_get_postgres_sync_engine_reuses_cached_engine_for_same_redacted_url(monkeypatch) -> None:
    env = {
        "NEXA_SERVER_DB_HOST": "db.internal",
        "NEXA_SERVER_DB_PORT": "5432",
        "NEXA_SERVER_DB_NAME": "nexa",
        "NEXA_SERVER_DB_USER": "nexa",
        "NEXA_SERVER_DB_PASSWORD": "secret",
    }
    created = []

    def _fake_create(settings, *, password):
        engine = object()
        created.append((settings, password, engine))
        return engine

    monkeypatch.setattr("src.server.pg.engine.create_sync_engine_from_settings", _fake_create)
    reset_postgres_engine_cache()
    try:
        engine_a = get_postgres_sync_engine(env)
        engine_b = get_postgres_sync_engine(env)
        assert engine_a is engine_b
        assert len(created) == 1
    finally:
        reset_postgres_engine_cache()

def test_check_provider_bootstrap_posture_is_degraded_but_ready_without_provider_keys(monkeypatch) -> None:
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    result = check_provider_bootstrap_posture()

    assert result["ready"] is True
    assert result["status"] == "degraded"


def test_build_postgres_readiness_checks_integrates_sync_readyz_payload() -> None:
    from src.server.health_routes import build_health_router

    checks = ReadinessChecks(
        db_check=lambda: {"status": "ok", "ready": True},
        alembic_check=lambda: {"status": "ok", "ready": True},
        provider_check=lambda: {"status": "degraded", "ready": True},
    )
    app = FastAPI()
    app.include_router(
        build_health_router(
            db_check=checks.db_check,
            alembic_check=checks.alembic_check,
            provider_check=checks.provider_check,
        )
    )
    client = TestClient(app)
    response = client.get("/readyz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["checks"]["provider"]["status"] == "degraded"
    assert payload["status"] == "ready"


def test_build_default_readiness_checks_uses_postgres_mode_helpers(monkeypatch) -> None:
    class DummyAsyncEngine:
        url = "postgresql+asyncpg://nexa:secret@localhost:5432/nexa"

    engine = DummyAsyncEngine()
    sentinel = build_postgres_readiness_checks(engine)
    monkeypatch.setenv("NEXA_DEPENDENCY_MODE", "postgres")
    monkeypatch.setattr("src.server.dependency_factory.get_postgres_engine", lambda: engine)
    monkeypatch.setattr("src.server.dependency_factory.build_postgres_readiness_checks", lambda resolved: sentinel)

    checks = build_default_readiness_checks()
    assert checks is sentinel
