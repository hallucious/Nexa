from __future__ import annotations

"""External plugin sandbox worker (Step43).

Run an untrusted callable in a separate process with a hard timeout.

Design notes:
- Uses multiprocessing with "spawn" for Windows compatibility.
- Only supports calling a top-level function in a module loaded from a file path.
- Arguments and return value must be JSON-serializable for transport.
"""

import importlib.util
import json
import multiprocessing as mp
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    value: Optional[Any]
    error: Optional[str]
    kind: str  # "OK" | "TIMEOUT" | "CRASH"


def _load_func(module_path: Path, func_name: str):
    spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"spec_load_failed: {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    fn = getattr(mod, func_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(f"callable_not_found: {func_name}")
    return fn


def _child_entry(q: "mp.Queue[str]", module_path_s: str, func_name: str, kwargs: Dict[str, Any]) -> None:
    try:
        module_path = Path(module_path_s)
        fn = _load_func(module_path, func_name)
        out = fn(**kwargs)
        q.put(json.dumps({"ok": True, "value": out, "error": None, "kind": "OK"}, ensure_ascii=False))
    except Exception:
        q.put(
            json.dumps(
                {
                    "ok": False,
                    "value": None,
                    "error": traceback.format_exc(),
                    "kind": "CRASH",
                },
                ensure_ascii=False,
            )
        )


def run_in_sandbox(
    *,
    module_path: Path,
    func_name: str,
    kwargs: Dict[str, Any],
    timeout_ms: int,
) -> SandboxResult:
    """Run callable in a subprocess.

    Raises no exception; returns SandboxResult(kind=TIMEOUT/CRASH) on failure.
    """
    ctx = mp.get_context("spawn")
    q: "mp.Queue[str]" = ctx.Queue(maxsize=1)

    p = ctx.Process(target=_child_entry, args=(q, str(module_path), func_name, kwargs))
    p.daemon = True
    p.start()

    p.join(timeout=max(0.0, timeout_ms) / 1000.0)

    if p.is_alive():
        try:
            p.terminate()
        except Exception:
            pass
        try:
            p.join(timeout=0.2)
        except Exception:
            pass
        return SandboxResult(ok=False, value=None, error="external plugin timeout", kind="TIMEOUT")

    try:
        payload = q.get_nowait()
        data = json.loads(payload)
        return SandboxResult(
            ok=bool(data.get("ok")),
            value=data.get("value"),
            error=data.get("error"),
            kind=str(data.get("kind") or ""),
        )
    except Exception as e:
        return SandboxResult(ok=False, value=None, error=f"external plugin crash: {e}", kind="CRASH")
