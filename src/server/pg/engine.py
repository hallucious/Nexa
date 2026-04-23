from __future__ import annotations

import os
from typing import Any, Mapping

from src.server.database_foundation import build_postgres_connection_url, load_postgres_connection_settings_from_env
from src.server.database_models import PostgresConnectionSettings

try:  # pragma: no cover - availability differs by environment
    from sqlalchemy import create_engine
    from sqlalchemy.engine import Engine as SyncEngine
except ModuleNotFoundError:  # pragma: no cover
    SyncEngine = Any  # type: ignore[misc,assignment]
    create_engine = None  # type: ignore[assignment]

try:  # pragma: no cover - availability differs by environment
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
except ModuleNotFoundError:  # pragma: no cover
    AsyncEngine = Any  # type: ignore[misc,assignment]
    create_async_engine = None  # type: ignore[assignment]

_ENGINE_CACHE: dict[str, AsyncEngine] = {}
_SYNC_ENGINE_CACHE: dict[str, SyncEngine] = {}


def resolve_database_password(
    settings: PostgresConnectionSettings,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    env_map = env if env is not None else os.environ
    password = str(env_map.get(settings.password_env_var, "")).strip()
    if not password:
        raise RuntimeError(
            "Postgres password environment variable is not configured: "
            f"{settings.password_env_var}"
        )
    return password


def build_asyncpg_connection_url(
    settings: PostgresConnectionSettings,
    *,
    password: str,
    redact_password: bool = False,
) -> str:
    sync_url = build_postgres_connection_url(
        settings,
        password=password,
        redact_password=redact_password,
    )
    return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)


def build_psycopg_connection_url(
    settings: PostgresConnectionSettings,
    *,
    password: str,
    redact_password: bool = False,
) -> str:
    sync_url = build_postgres_connection_url(
        settings,
        password=password,
        redact_password=redact_password,
    )
    return sync_url.replace("postgresql://", "postgresql+psycopg://", 1)


def create_async_engine_from_settings(
    settings: PostgresConnectionSettings,
    *,
    password: str,
) -> AsyncEngine:
    if create_async_engine is None:
        raise ModuleNotFoundError("sqlalchemy is required to create a Postgres async engine")
    return create_async_engine(
        build_asyncpg_connection_url(settings, password=password),
        pool_pre_ping=True,
        future=True,
    )


def create_sync_engine_from_settings(
    settings: PostgresConnectionSettings,
    *,
    password: str,
) -> SyncEngine:
    if create_engine is None:
        raise ModuleNotFoundError("sqlalchemy is required to create a Postgres sync engine")
    return create_engine(
        build_psycopg_connection_url(settings, password=password),
        pool_pre_ping=True,
        future=True,
    )


def create_async_engine_from_env(
    env: Mapping[str, str] | None = None,
) -> AsyncEngine:
    settings = load_postgres_connection_settings_from_env(env)
    password = resolve_database_password(settings, env=env)
    return create_async_engine_from_settings(settings, password=password)


def create_sync_engine_from_env(
    env: Mapping[str, str] | None = None,
) -> SyncEngine:
    settings = load_postgres_connection_settings_from_env(env)
    password = resolve_database_password(settings, env=env)
    return create_sync_engine_from_settings(settings, password=password)


def get_postgres_engine(
    env: Mapping[str, str] | None = None,
) -> AsyncEngine:
    settings = load_postgres_connection_settings_from_env(env)
    password = resolve_database_password(settings, env=env)
    cache_key = build_asyncpg_connection_url(settings, password=password, redact_password=True)
    engine = _ENGINE_CACHE.get(cache_key)
    if engine is None:
        engine = create_async_engine_from_settings(settings, password=password)
        _ENGINE_CACHE[cache_key] = engine
    return engine


def get_postgres_sync_engine(
    env: Mapping[str, str] | None = None,
) -> SyncEngine:
    settings = load_postgres_connection_settings_from_env(env)
    password = resolve_database_password(settings, env=env)
    cache_key = build_psycopg_connection_url(settings, password=password, redact_password=True)
    engine = _SYNC_ENGINE_CACHE.get(cache_key)
    if engine is None:
        engine = create_sync_engine_from_settings(settings, password=password)
        _SYNC_ENGINE_CACHE[cache_key] = engine
    return engine


def reset_postgres_engine_cache() -> None:
    _ENGINE_CACHE.clear()
    _SYNC_ENGINE_CACHE.clear()
