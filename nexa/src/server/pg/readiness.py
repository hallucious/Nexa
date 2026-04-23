from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:  # pragma: no cover - availability differs by environment
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
except ModuleNotFoundError:  # pragma: no cover
    Config = None  # type: ignore[assignment]
    MigrationContext = None  # type: ignore[assignment]
    ScriptDirectory = None  # type: ignore[assignment]

try:  # pragma: no cover - availability differs by environment
    from sqlalchemy import text
except ModuleNotFoundError:  # pragma: no cover
    text = None  # type: ignore[assignment]

from src.server.health_routes import ReadinessChecks


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_alembic_ini_path() -> Path:
    return Path(os.environ.get("NEXA_ALEMBIC_INI_PATH") or (_project_root() / "alembic.ini"))


def _default_alembic_script_location() -> Path:
    return Path(os.environ.get("NEXA_ALEMBIC_SCRIPT_LOCATION") or (_project_root() / "alembic"))


def _provider_env_keys() -> tuple[str, ...]:
    return (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    )


async def check_database_connection(engine: Any) -> dict[str, Any]:
    if text is None:
        raise ModuleNotFoundError("sqlalchemy is required to run Postgres readiness checks")
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ok", "ready": True}
    except Exception as exc:  # pragma: no cover - exercised through tests with monkeypatch/fakes
        return {
            "status": "connection_failed",
            "ready": False,
            "reason": exc.__class__.__name__,
            "detail": str(exc),
        }


async def _current_heads(engine: Any) -> tuple[str, ...]:
    if MigrationContext is None:
        raise ModuleNotFoundError("alembic is required to inspect database migration heads")
    async with engine.connect() as connection:
        def _read_heads(sync_connection):
            context = MigrationContext.configure(sync_connection)
            return tuple(context.get_current_heads())

        return await connection.run_sync(_read_heads)


async def check_alembic_head_alignment(
    engine: Any,
    *,
    alembic_ini_path: str | Path | None = None,
    script_location: str | Path | None = None,
) -> dict[str, Any]:
    if Config is None or ScriptDirectory is None:
        raise ModuleNotFoundError("alembic is required to run migration readiness checks")

    resolved_ini = Path(alembic_ini_path) if alembic_ini_path is not None else _default_alembic_ini_path()
    resolved_script_location = Path(script_location) if script_location is not None else _default_alembic_script_location()
    if not resolved_ini.exists():
        return {
            "status": "missing_alembic_ini",
            "ready": False,
            "path": str(resolved_ini),
        }
    if not resolved_script_location.exists():
        return {
            "status": "missing_script_location",
            "ready": False,
            "path": str(resolved_script_location),
        }
    try:
        config = Config(str(resolved_ini))
        config.set_main_option("script_location", str(resolved_script_location))
        script_directory = ScriptDirectory.from_config(config)
        head_revisions = tuple(script_directory.get_heads())
        current_revisions = await _current_heads(engine)
    except Exception as exc:  # pragma: no cover - exercised through tests with monkeypatch/fakes
        return {
            "status": "alembic_check_failed",
            "ready": False,
            "reason": exc.__class__.__name__,
            "detail": str(exc),
        }

    if not head_revisions:
        return {
            "status": "missing_head_revision",
            "ready": False,
            "head_revisions": (),
            "current_revisions": current_revisions,
        }
    if current_revisions == head_revisions:
        return {
            "status": "ok",
            "ready": True,
            "head_revisions": head_revisions,
            "current_revisions": current_revisions,
        }
    return {
        "status": "out_of_date",
        "ready": False,
        "head_revisions": head_revisions,
        "current_revisions": current_revisions,
    }


def check_provider_bootstrap_posture() -> dict[str, Any]:
    configured_keys = tuple(key for key in _provider_env_keys() if str(os.environ.get(key, "")).strip())
    if configured_keys:
        return {
            "status": "ok",
            "ready": True,
            "configured_provider_keys": configured_keys,
        }
    return {
        "status": "degraded",
        "ready": True,
        "reason": "no_provider_keys_configured",
        "configured_provider_keys": (),
    }


def build_postgres_readiness_checks(engine: Any) -> ReadinessChecks:
    return ReadinessChecks(
        db_check=lambda: check_database_connection(engine),
        alembic_check=lambda: check_alembic_head_alignment(engine),
        provider_check=check_provider_bootstrap_posture,
    )
