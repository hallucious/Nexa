from __future__ import annotations

"""src.platform.sandbox_worker

Step43: External plugin sandbox wrapper.

Design constraints (tests):
- External loader returns objects that expose `.call(**kwargs) -> (SandboxResult, value)`.
- SandboxResult must expose `.success` and `.timeout` booleans.
- Timeouts must be reliable even on very small budgets (delegated to safe_exec.safe_call).

Implementation choice:
- Thread-based isolation (same process) using safe_exec.safe_call.
  The project already uses this approach for provider/plugin calls (Step37).
  This is sufficient for the unit tests: we need bounded latency + structured
  failure, not OS-level process isolation.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .safe_exec import safe_call


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    value: Optional[Any]
    error: Optional[str]
    kind: str  # "OK" | "TIMEOUT" | "CRASH"

    @property
    def success(self) -> bool:
        # Back-compat alias expected by tests
        return bool(self.ok)

    @property
    def timeout(self) -> bool:
        return self.kind == "TIMEOUT"


class SandboxWorker:
    """Executes a callable with a time budget and returns a structured result."""

    def call(self, fn: Callable[[], Any], *, timeout_ms: int) -> SandboxResult:
        res = safe_call(fn, timeout_ms=timeout_ms)

        if res.ok:
            return SandboxResult(ok=True, value=res.value, error=None, kind="OK")

        if res.timed_out:
            return SandboxResult(ok=False, value=None, error="TIMEOUT", kind="TIMEOUT")

        # Crash path
        return SandboxResult(ok=False, value=None, error=res.error, kind="CRASH")



def _load_callable(module_path, func_name: str):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("external_plugin", str(module_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import plugin module: {module_path}")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    fn = getattr(mod, func_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(f"Callable not found: {func_name} in {module_path}")
    return fn


def run_in_sandbox(*, module_path, func_name: str, kwargs: dict, timeout_ms: int) -> SandboxResult:
    """Entry used by external_loader.SandboxedCallable.call(...).

    Load the callable before the timed execution window.  Under a busy full-suite
    run, import/thread startup latency can otherwise consume the small timeout
    budget and misclassify an immediate plugin crash as TIMEOUT.  The timeout
    budget is intended to bound the plugin call itself.
    """
    try:
        fn = _load_callable(module_path, func_name)
    except Exception as e:
        return SandboxResult(ok=False, value=None, error=f"{type(e).__name__}: {e}", kind="CRASH")

    def _invoke():
        return fn(**kwargs)

    res = safe_call(_invoke, timeout_ms=timeout_ms)

    if res.ok:
        return SandboxResult(ok=True, value=res.value, error=None, kind="OK")
    if res.timed_out:
        return SandboxResult(ok=False, value=None, error="TIMEOUT", kind="TIMEOUT")
    return SandboxResult(ok=False, value=None, error=res.error, kind="CRASH")
