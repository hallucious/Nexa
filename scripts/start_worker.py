#!/usr/bin/env python
"""Nexa async worker entrypoint.

Usage:
    python scripts/start_worker.py

The worker uses arq with the NexaWorkerSettings class defined in
src/server/queue/worker_settings.py.

Environment variables (see worker_settings.py and redis_client.py for full list):
    NEXA_REDIS_HOST         Redis host (default: localhost)
    NEXA_REDIS_PORT         Redis port (default: 6379)
    NEXA_WORKER_MAX_JOBS    Maximum concurrent jobs (default: 4)
    NEXA_WORKER_JOB_TIMEOUT Job timeout in seconds (default: 900)
    NEXA_SERVER_DB_*        Postgres connection settings (see database_foundation.py)
"""
from __future__ import annotations

import asyncio
import sys
import os

# Ensure project root is on path when invoked directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    try:
        import arq
    except ModuleNotFoundError:
        print(
            "ERROR: arq is not installed. "
            "Install it with: pip install 'arq>=0.26'",
            file=sys.stderr,
        )
        sys.exit(1)

    from src.server.queue.worker_settings import build_worker_settings_class

    worker_settings_cls = build_worker_settings_class()

    print("Starting Nexa worker …")
    print(f"  queue:    {worker_settings_cls.queue_name}")
    print(f"  max_jobs: {worker_settings_cls.max_jobs}")
    print(f"  timeout:  {worker_settings_cls.job_timeout}s")

    asyncio.run(arq.run_worker(worker_settings_cls))


if __name__ == "__main__":
    main()
