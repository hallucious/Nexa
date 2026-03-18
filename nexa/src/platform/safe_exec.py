from __future__ import annotations

"""src.platform.safe_exec

Thread-based "safety wrapper" for provider/plugin calls.

Important nuance (Windows timer granularity): a very small timeout (e.g. 1ms)
may not reliably interrupt a wait; the condition wait can oversleep.

Step37 test asserts that a call with `timeout_ms=1` must return a TIMEOUT
result even if the underlying work finishes later.

Implementation:
- Use Future.result(timeout=...)
- Additionally, if the measured latency exceeds timeout_ms, force TIMEOUT.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import concurrent.futures
import time


@dataclass(frozen=True)
class SafeCallResult:
    ok: bool
    value: Any
    error: Optional[str]
    timed_out: bool
    latency_ms: int


def safe_call(fn: Callable[[], Any], *, timeout_ms: Optional[int]) -> SafeCallResult:
    start = time.perf_counter()

    ok = False
    val: Any = None
    err: Optional[str] = None
    timed_out = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)

        try:
            if timeout_ms is None:
                val = fut.result()
                ok = True
            else:
                timeout_s = float(timeout_ms) / 1000.0
                val = fut.result(timeout=timeout_s)
                ok = True
        except concurrent.futures.TimeoutError:
            timed_out = True
            err = "TIMEOUT"
            ok = False
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            ok = False

    latency_ms = int((time.perf_counter() - start) * 1000)

    # Hard timeout: if we exceeded the budget, treat it as timeout even if the
    # Future returned (Windows may oversleep on very small timeouts).
    if timeout_ms is not None and latency_ms > int(timeout_ms):
        timed_out = True
        ok = False
        err = "TIMEOUT"
        val = None

    return SafeCallResult(ok=ok, value=val, error=err, timed_out=timed_out, latency_ms=latency_ms)


def safe_call2(fn: Callable[[], Any], *, timeout_ms: Optional[int]) -> Tuple[bool, Any, Optional[str], bool, int]:
    res = safe_call(fn, timeout_ms=timeout_ms)
    return res.ok, res.value, res.error, res.timed_out, res.latency_ms
