from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError


@dataclass
class SafeCallResult:
    ok: bool
    value: Any
    timed_out: bool
    error: Optional[str]
    latency_ms: int


def safe_call(*, fn: Callable[[], Any], timeout_ms: Optional[int]) -> SafeCallResult:
    """Run fn() with exception containment and a best-effort timeout.

    Timeout semantics:
    - timeout_ms is in *milliseconds*.
    - If timeout_ms is None: no timeout, still exception-contained.

    Notes:
    - Uses threads (portable on Windows).
    - Timeout is "soft": we return immediately with TIMEOUT, but cannot forcibly
      kill Python code already running in the worker thread.
    """

    started = time.perf_counter()

    # No timeout requested -> direct call, still contained.
    if timeout_ms is None:
        try:
            v = fn()
            latency_ms = int((time.perf_counter() - started) * 1000)
            return SafeCallResult(ok=True, value=v, timed_out=False, error=None, latency_ms=latency_ms)
        except Exception as e:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - started) * 1000)
            return SafeCallResult(
                ok=False,
                value=None,
                timed_out=False,
                error=f"{type(e).__name__}: {e}",
                latency_ms=latency_ms,
            )

    # Defensive: treat negative as 0ms.
    timeout_ms_i = int(timeout_ms)
    if timeout_ms_i < 0:
        timeout_ms_i = 0

    # Convert ms -> seconds for Future.result(timeout=...).
    timeout_s = float(timeout_ms_i) / 1000.0

    ex = ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn)

    try:
        v = fut.result(timeout=timeout_s)
        latency_ms = int((time.perf_counter() - started) * 1000)
        ex.shutdown(wait=False)
        return SafeCallResult(ok=True, value=v, timed_out=False, error=None, latency_ms=latency_ms)
    except FuturesTimeoutError:
        # Best-effort cancel; may fail if already running.
        fut.cancel()
        latency_ms = int((time.perf_counter() - started) * 1000)
        ex.shutdown(wait=False)
        return SafeCallResult(ok=False, value=None, timed_out=True, error="TIMEOUT", latency_ms=latency_ms)
    except Exception as e:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        ex.shutdown(wait=False)
        return SafeCallResult(
            ok=False,
            value=None,
            timed_out=False,
            error=f"{type(e).__name__}: {e}",
            latency_ms=latency_ms,
        )
