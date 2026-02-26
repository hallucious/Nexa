from __future__ import annotations

"""Injection Registry Contract v1 (Step41-B2, Option B).

This module provides:
- InjectionSpec: (target, key, version, determinism_required, timeout_ms)
- InjectionCallResult: normalized result for any injection call
- InjectionHandle: wraps an injected callable/object and enforces observability
- InjectionRegistry: load-time validation + handle retrieval

Design goals:
- Backward compatible with existing v0 GateContext.providers/context/plugins dicts.
- Does NOT change Step43 SandboxedCallable API; registry can wrap it.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Callable
import time

from src.pipeline.observability import append_observability_event


# -----------------------------------------------------------------------------
# Contracts
# -----------------------------------------------------------------------------

ERROR_TIMEOUT = "timeout"
ERROR_CRASH = "crash"
ERROR_CONTRACT = "contract_error"
ERROR_LOAD = "load_error"
ERROR_SECURITY = "security_violation"
ERROR_UNKNOWN = "unknown_error"

_ALLOWED_ERROR_CODES = {
    ERROR_TIMEOUT,
    ERROR_CRASH,
    ERROR_CONTRACT,
    ERROR_LOAD,
    ERROR_SECURITY,
    ERROR_UNKNOWN,
}


@dataclass(frozen=True)
class InjectionSpec:
    target: str
    key: str
    version: str = "0.0.0"
    determinism_required: bool = False
    timeout_ms: Optional[int] = None

    def tuple_key(self) -> Tuple[str, str]:
        return (self.target, self.key)


@dataclass
class InjectionCallResult:
    success: bool
    error_code: Optional[str]
    error: Optional[str]
    meta: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    spec_version: str = "0.0.0"
    determinism_required: bool = False

    def __post_init__(self) -> None:
        if self.error_code is not None and self.error_code not in _ALLOWED_ERROR_CODES:
            # Normalize unknown codes to ERROR_UNKNOWN
            self.error_code = ERROR_UNKNOWN


# -----------------------------------------------------------------------------
# Handle
# -----------------------------------------------------------------------------

class InjectionHandle:
    def __init__(
        self,
        *,
        spec: InjectionSpec,
        impl: Any,
        run_dir: Optional[str] = None,
        event_name: str = "INJECTION_CALL",
    ) -> None:
        self.spec = spec
        self._impl = impl
        self._run_dir = run_dir
        self._event_name = event_name

    def call(self, **kwargs: Any) -> Tuple[InjectionCallResult, Any]:
        start = time.perf_counter()
        result: InjectionCallResult
        value: Any = None

        try:
            # Case A: Step43 SandboxedCallable-like: has call(**kwargs) -> (res, val)
            call_fn = getattr(self._impl, "call", None)
            if callable(call_fn):
                res, val = call_fn(**kwargs)
                value = val

                # SandboxResult contract used in Step43 tests
                success = bool(getattr(res, "success", False))
                timeout = bool(getattr(res, "timeout", False))
                err_msg = getattr(res, "error", None)

                if success:
                    result = InjectionCallResult(
                        success=True,
                        error_code=None,
                        error=None,
                        meta={"kind": getattr(res, "kind", None)},
                        spec_version=self.spec.version,
                        determinism_required=self.spec.determinism_required,
                    )
                else:
                    if timeout:
                        ec = ERROR_TIMEOUT
                    else:
                        ec = ERROR_CRASH if err_msg else ERROR_UNKNOWN
                    result = InjectionCallResult(
                        success=False,
                        error_code=ec,
                        error=str(err_msg) if err_msg is not None else None,
                        meta={"kind": getattr(res, "kind", None)},
                        spec_version=self.spec.version,
                        determinism_required=self.spec.determinism_required,
                    )
            else:
                # Case B: provider-like object with generate_text(**kwargs) -> (text, raw, err)
                gen = getattr(self._impl, "generate_text", None)
                if callable(gen):
                    args = kwargs.pop("__args", ())
                    if not isinstance(args, tuple):
                        args = tuple(args) if isinstance(args, (list,)) else (args,)
                    ret = gen(*args, **kwargs)
                    # Normalize: expected (text, raw, err)
                    text = ""
                    raw: Dict[str, Any] = {}
                    err = None
                    if isinstance(ret, tuple) and len(ret) >= 3:
                        text, raw, err = ret[0], ret[1], ret[2]
                    else:
                        # Non-standard: treat as success with value
                        value = ret
                        result = InjectionCallResult(
                            success=True,
                            error_code=None,
                            error=None,
                            meta={"contract": "nonstandard_return"},
                            spec_version=self.spec.version,
                            determinism_required=self.spec.determinism_required,
                        )
                        return self._finalize(start, result, value)

                    value = ret
                    success = err is None
                    result = InjectionCallResult(
                        success=success,
                        error_code=None if success else ERROR_UNKNOWN,
                        error=None if success else f"{type(err).__name__}: {err}",
                        meta={"raw": raw if isinstance(raw, dict) else {}},
                        spec_version=self.spec.version,
                        determinism_required=self.spec.determinism_required,
                    )
                else:
                    raise TypeError("Injected implementation is not callable and has no generate_text/call")
        except TimeoutError as e:
            result = InjectionCallResult(
                success=False,
                error_code=ERROR_TIMEOUT,
                error=str(e),
                meta={},
                spec_version=self.spec.version,
                determinism_required=self.spec.determinism_required,
            )
        except Exception as e:  # noqa: BLE001
            result = InjectionCallResult(
                success=False,
                error_code=ERROR_CRASH,
                error=f"{type(e).__name__}: {e}",
                meta={},
                spec_version=self.spec.version,
                determinism_required=self.spec.determinism_required,
            )

        return self._finalize(start, result, value)

    def _finalize(self, start: float, result: InjectionCallResult, value: Any) -> Tuple[InjectionCallResult, Any]:
        dur = int((time.perf_counter() - start) * 1000.0)
        result.duration_ms = dur

        if self._run_dir:
            append_observability_event(
                run_dir=self._run_dir,
                event={
                    "event": self._event_name,
                    "target": self.spec.target,
                    "key": self.spec.key,
                    "spec_version": self.spec.version,
                    "success": result.success,
                    "error": result.error_code,
                    "duration_ms": dur,
                    "determinism_required": bool(self.spec.determinism_required),
                },
            )
        return result, value


# -----------------------------------------------------------------------------
# Registry
# -----------------------------------------------------------------------------

class InjectionRegistryError(ValueError):
    pass


class InjectionRegistry:
    def __init__(self, *, run_dir: Optional[str] = None) -> None:
        self._run_dir = run_dir
        self._specs: Dict[Tuple[str, str], InjectionSpec] = {}
        self._impls: Dict[Tuple[str, str], Any] = {}

    def register(self, *, spec: InjectionSpec, impl: Any) -> None:
        tup = spec.tuple_key()
        if tup in self._specs:
            existing = self._specs[tup]
            if existing.version != spec.version:
                raise InjectionRegistryError(
                    f"injection_version_mismatch: {tup} existing={existing.version} new={spec.version}"
                )
            raise InjectionRegistryError(f"injection_duplicate: {tup}")
        self._specs[tup] = spec
        self._impls[tup] = impl

    def get(self, *, target: str, key: str) -> InjectionHandle:
        tup = (target, key)
        if tup not in self._specs:
            raise InjectionRegistryError(f"injection_missing: {tup}")
        return InjectionHandle(spec=self._specs[tup], impl=self._impls[tup], run_dir=self._run_dir)

    @classmethod
    def from_gate_context(cls, ctx: Any) -> "InjectionRegistry":
        """Build a registry from legacy GateContext dicts (providers/plugins/context).

        This is a compatibility bridge so existing tests and call sites keep working.
        """
        run_dir = getattr(ctx, "run_dir", None)
        reg = cls(run_dir=str(run_dir) if run_dir else None)

        providers = getattr(ctx, "providers", None) or {}
        plugins = getattr(ctx, "plugins", None) or {}
        context = getattr(ctx, "context", None) or {}

        if isinstance(providers, dict):
            for k, v in providers.items():
                if v is None:
                    continue
                reg.register(spec=InjectionSpec(target="providers", key=str(k), version="0.0.0"), impl=v)

        if isinstance(plugins, dict):
            for k, v in plugins.items():
                if v is None:
                    continue
                reg.register(spec=InjectionSpec(target="plugins", key=str(k), version="0.0.0"), impl=v)
        if isinstance(context, dict):
            # Plain context bucket
            for k, v in context.items():
                if k == "plugins":
                    continue
                if v is None:
                    continue
                reg.register(spec=InjectionSpec(target="context", key=str(k), version="0.0.0"), impl=v)

            # Expose context.plugins as a separate target, matching platform plugin_discovery rules.
            ctx_plugins = context.get("plugins")
            if isinstance(ctx_plugins, dict):
                for k, v in ctx_plugins.items():
                    if v is None:
                        continue
                    reg.register(spec=InjectionSpec(target="context.plugins", key=str(k), version="0.0.0"), impl=v)

        return reg

