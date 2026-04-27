"""arq worker settings for the Nexa async queue substrate.

arq (https://arq-docs.helpmanual.io/) is used as the queue runtime.
This module owns the WorkerSettings class that arq uses to start and
configure worker processes.

Environment variables consumed (beyond Redis settings):
    NEXA_WORKER_MAX_JOBS       (default: 4)
    NEXA_WORKER_JOB_TIMEOUT    (default: 900  — 15 minutes, seconds)
    NEXA_WORKER_KEEP_RESULT    (default: 3600 — 1 hour, seconds)
    NEXA_WORKER_RETRY_JOBS     (default: false)
    NEXA_WORKER_QUEUE_NAME     (default: nexa_run_queue)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from src.server.queue.redis_client import build_redis_url, load_redis_settings_from_env

# Queue name used by all producers and consumers.
NEXA_RUN_QUEUE_NAME: str = "nexa_run_queue"

# Job function name as registered with arq.
NEXA_RUN_JOB_FUNCTION_NAME: str = "execute_queued_run"


@dataclass(frozen=True)
class QueuePolicy:
    """Immutable worker/queue policy snapshot loaded from environment."""

    queue_name: str
    max_jobs: int
    job_timeout_s: int
    keep_result_s: int
    retry_jobs: bool
    job_function_name: str

    def __post_init__(self) -> None:
        if not self.queue_name.strip():
            raise ValueError("QueuePolicy.queue_name must be non-empty")
        if self.max_jobs < 1:
            raise ValueError("QueuePolicy.max_jobs must be >= 1")
        if self.job_timeout_s < 1:
            raise ValueError("QueuePolicy.job_timeout_s must be >= 1")
        if self.keep_result_s < 0:
            raise ValueError("QueuePolicy.keep_result_s must be >= 0")


def load_queue_policy_from_env(
    *,
    env: Optional[dict[str, str]] = None,
) -> QueuePolicy:
    """Load queue policy from environment variables, falling back to safe defaults."""
    env_map = env if env is not None else os.environ

    queue_name = env_map.get("NEXA_WORKER_QUEUE_NAME", NEXA_RUN_QUEUE_NAME).strip() or NEXA_RUN_QUEUE_NAME

    try:
        max_jobs = int(env_map.get("NEXA_WORKER_MAX_JOBS", "4"))
        if max_jobs < 1:
            max_jobs = 4
    except ValueError:
        max_jobs = 4

    try:
        job_timeout_s = int(env_map.get("NEXA_WORKER_JOB_TIMEOUT", "900"))
        if job_timeout_s < 1:
            job_timeout_s = 900
    except ValueError:
        job_timeout_s = 900

    try:
        keep_result_s = int(env_map.get("NEXA_WORKER_KEEP_RESULT", "3600"))
        if keep_result_s < 0:
            keep_result_s = 3600
    except ValueError:
        keep_result_s = 3600

    retry_jobs_str = env_map.get("NEXA_WORKER_RETRY_JOBS", "false").strip().lower()
    retry_jobs = retry_jobs_str in {"true", "1", "yes"}

    return QueuePolicy(
        queue_name=queue_name,
        max_jobs=max_jobs,
        job_timeout_s=job_timeout_s,
        keep_result_s=keep_result_s,
        retry_jobs=retry_jobs,
        job_function_name=NEXA_RUN_JOB_FUNCTION_NAME,
    )


def build_worker_settings_class(
    *,
    env: Optional[dict[str, str]] = None,
) -> Any:
    """Return an arq-compatible WorkerSettings class.

    arq discovers the worker class by convention — the returned class is used
    as the ``WorkerSettings`` in the arq worker entrypoint.

    Returns a plain class object (not an instance) so arq can introspect it.

    Raises ModuleNotFoundError if arq is not installed.
    """
    try:
        from arq import cron  # noqa: F401 — confirms arq is present
        from arq.connections import RedisSettings as ArqRedisSettings
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "arq is required for the Nexa async queue worker. "
            "Install it with: pip install 'arq>=0.26'"
        ) from exc

    # Import here to avoid circular dependency at module load time.
    from src.server.queue.worker_functions import execute_queued_run  # noqa: F401

    redis_settings = load_redis_settings_from_env(env=env)
    queue_policy = load_queue_policy_from_env(env=env)
    redis_url = build_redis_url(redis_settings)

    class NexaWorkerSettings:  # noqa: D101 — internal arq convention class
        functions = [execute_queued_run]
        redis_settings = ArqRedisSettings.from_dsn(redis_url)
        queue_name = queue_policy.queue_name
        max_jobs = queue_policy.max_jobs
        job_timeout = queue_policy.job_timeout_s
        keep_result = queue_policy.keep_result_s
        retry_jobs = queue_policy.retry_jobs
        handle_signals = True

    return NexaWorkerSettings
