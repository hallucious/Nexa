"""Redis client factory for the Nexa async queue substrate.

This module provides a thin wrapper around the Redis client that:
- reads connection settings from environment variables,
- exposes a factory usable by both the API and worker processes,
- degrades gracefully when redis is not installed (import-safe),
- never assumes a live Redis connection in test environments.

Environment variables consumed:
    NEXA_REDIS_HOST      (default: localhost)
    NEXA_REDIS_PORT      (default: 6379)
    NEXA_REDIS_DB        (default: 0)
    NEXA_REDIS_PASSWORD  (optional; name of the env var holding the password)
    NEXA_REDIS_SSL       (default: false)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

try:  # pragma: no cover - optional dependency
    import redis.asyncio as aioredis
    from redis.asyncio import Redis as AsyncRedis
except ModuleNotFoundError:  # pragma: no cover
    aioredis = None  # type: ignore[assignment]
    AsyncRedis = Any  # type: ignore[misc,assignment]


@dataclass(frozen=True)
class RedisConnectionSettings:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 20

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("RedisConnectionSettings.host must be non-empty")
        if not (0 < self.port < 65536):
            raise ValueError(f"RedisConnectionSettings.port must be 1–65535, got {self.port}")
        if self.db < 0:
            raise ValueError(f"RedisConnectionSettings.db must be >= 0, got {self.db}")


def load_redis_settings_from_env(
    *,
    env: Optional[dict[str, str]] = None,
) -> RedisConnectionSettings:
    """Load Redis connection settings from environment variables.

    Falls back to safe defaults so tests can import this module without
    environment configuration.
    """
    env_map = env if env is not None else os.environ

    host = env_map.get("NEXA_REDIS_HOST", "localhost").strip() or "localhost"
    port_str = env_map.get("NEXA_REDIS_PORT", "6379").strip()
    db_str = env_map.get("NEXA_REDIS_DB", "0").strip()
    password_env_var = env_map.get("NEXA_REDIS_PASSWORD", "").strip()
    ssl_str = env_map.get("NEXA_REDIS_SSL", "false").strip().lower()

    try:
        port = int(port_str)
    except ValueError:
        port = 6379
    try:
        db = int(db_str)
    except ValueError:
        db = 0

    password: Optional[str] = None
    if password_env_var:
        password = env_map.get(password_env_var, "").strip() or None

    return RedisConnectionSettings(
        host=host,
        port=port,
        db=db,
        password=password,
        ssl=(ssl_str in {"true", "1", "yes"}),
    )


def build_redis_url(settings: RedisConnectionSettings) -> str:
    """Return a redis:// or rediss:// URL from settings.

    This URL is accepted by both the redis-py client and arq worker settings.
    """
    scheme = "rediss" if settings.ssl else "redis"
    if settings.password:
        return f"{scheme}://:{settings.password}@{settings.host}:{settings.port}/{settings.db}"
    return f"{scheme}://{settings.host}:{settings.port}/{settings.db}"


def build_async_redis_client(
    settings: Optional[RedisConnectionSettings] = None,
    *,
    env: Optional[dict[str, str]] = None,
) -> "AsyncRedis":
    """Build an async Redis client from settings or env vars.

    Raises ModuleNotFoundError if redis is not installed.
    """
    if aioredis is None:
        raise ModuleNotFoundError(
            "redis[asyncio] is required for the Nexa async queue substrate. "
            "Install it with: pip install 'redis>=5.0'"
        )
    resolved = settings or load_redis_settings_from_env(env=env)
    url = build_redis_url(resolved)
    return aioredis.from_url(
        url,
        socket_timeout=resolved.socket_timeout,
        socket_connect_timeout=resolved.socket_connect_timeout,
        max_connections=resolved.max_connections,
        decode_responses=False,
    )


async def ping_redis(
    settings: Optional[RedisConnectionSettings] = None,
    *,
    env: Optional[dict[str, str]] = None,
) -> bool:
    """Return True if Redis is reachable, False otherwise.

    Never raises; designed for health-check use.
    """
    try:
        client = build_async_redis_client(settings=settings, env=env)
        result = await client.ping()
        await client.aclose()
        return bool(result)
    except Exception:  # noqa: BLE001
        return False
