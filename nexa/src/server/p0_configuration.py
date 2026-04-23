from __future__ import annotations

import os


def _validate_p0_configuration(
    idempotency_window_s: int,
    max_run_duration_s: int,
) -> None:
    """Validate P0 timing guards.

    RuntimeError is required here rather than ``assert`` so that the guard
    remains active under optimized Python runtimes (``-O`` / ``-OO``).
    """
    if idempotency_window_s <= max_run_duration_s:
        raise RuntimeError(
            f"Configuration error: IDEMPOTENCY_WINDOW_S ({idempotency_window_s}s) "
            f"must be greater than NEXA_P0_MAX_RUN_DURATION_S ({max_run_duration_s}s). "
            "A run that outlives the idempotency window can be submitted twice. "
            "Raise IDEMPOTENCY_WINDOW_S or lower NEXA_P0_MAX_RUN_DURATION_S."
        )


def get_idempotency_window_s() -> int:
    return int(os.environ.get("IDEMPOTENCY_WINDOW_S", "86400"))


def get_max_run_duration_s() -> int:
    return int(os.environ.get("NEXA_P0_MAX_RUN_DURATION_S", "3600"))
