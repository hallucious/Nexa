from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .safe_exec import safe_call


@dataclass
class PluginResult:
    """Plugin execution result envelope.

    Backward-compatible fields preserved:
    - output
    - latency_ms

    Additions (for PLUGIN-CONTRACT v1.0.0 alignment):
    - reason_code: standardized failure taxonomy
    - stage: PRE | CORE | POST (best-effort, passed by caller)
    - resource_usage: optional structured usage report

    Convenience:
    - data: alias for output
    - metrics: dict containing latency_ms + resource_usage
    """

    success: bool
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    latency_ms: int
    reason_code: Optional[str] = None
    stage: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        return self.output

    @property
    def metrics(self) -> Dict[str, Any]:
        return {"latency_ms": int(self.latency_ms), "resource_usage": self.resource_usage}


class Plugin:
    name: str

    def execute(self, **kwargs: Any) -> PluginResult:
        raise NotImplementedError


class DummyEchoPlugin(Plugin):
    """Minimal v0.1 plugin for contract verification only."""

    def __init__(self) -> None:
        self.name = "dummy_echo"

    def execute(self, **kwargs: Any) -> PluginResult:
        started = time.perf_counter()
        stage = kwargs.get("stage")
        try:
            result = {"echo": dict(kwargs)}
            success = True
            error = None
            reason_code = None
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "SYSTEM.unexpected_exception"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(
            success=success,
            output=result,
            error=error,
            latency_ms=latency_ms,
            reason_code=reason_code,
            stage=str(stage) if stage is not None else None,
        )


class FileWritePlugin(Plugin):
    """Write text content to a file (v0.1)."""

    def __init__(self) -> None:
        self.name = "file_write"

    def execute(self, **kwargs: Any) -> PluginResult:
        """
        Required kwargs:
          - path: str | Path
          - content: str
        Optional:
          - encoding: str (default: utf-8)
          - mkdirs: bool (default: True)  # create parent dirs
          - overwrite: bool (default: True)
          - stage: PRE|CORE|POST (ignored by behavior; recorded)
        """
        started = time.perf_counter()
        stage = kwargs.get("stage")
        try:
            path = kwargs.get("path")
            content = kwargs.get("content")
            encoding = kwargs.get("encoding", "utf-8")
            mkdirs = bool(kwargs.get("mkdirs", True))
            overwrite = bool(kwargs.get("overwrite", True))

            if path is None or content is None:
                raise ValueError("path and content are required")

            p = Path(path)
            if mkdirs:
                p.parent.mkdir(parents=True, exist_ok=True)

            if (not overwrite) and p.exists():
                raise FileExistsError(f"File exists and overwrite=False: {p}")

            p.write_text(str(content), encoding=str(encoding))

            result = {
                "path": str(p),
                "bytes": len(str(content).encode(str(encoding))),
            }
            success = True
            error = None
            reason_code = None
        except (ValueError, TypeError) as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.invalid_input"
        except FileExistsError as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.execution_error"
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.execution_error"

        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(
            success=success,
            output=result,
            error=error,
            latency_ms=latency_ms,
            reason_code=reason_code,
            stage=str(stage) if stage is not None else None,
        )


class ExecutionPlugin(Plugin):
    """Executes a subprocess command and returns captured stdout/stderr."""

    def __init__(self) -> None:
        self.name = "exec"

    def execute(self, **kwargs: Any) -> PluginResult:
        started = time.perf_counter()
        stage = kwargs.get("stage")
        try:
            cmd = kwargs.get("cmd")
            cwd = kwargs.get("cwd")
            env = kwargs.get("env")
            timeout_s = kwargs.get("timeout_s")
            shell = bool(kwargs.get("shell", False))
            text_mode = bool(kwargs.get("text_mode", True))
            if cmd is None:
                raise ValueError("cmd is required")

            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                timeout=timeout_s,
                shell=shell,
                text=text_mode,
                capture_output=True,
            )
            result = {
                "args": getattr(proc, "args", cmd),
                "returncode": proc.returncode,
                "stdout": proc.stdout if proc.stdout is not None else "",
                "stderr": proc.stderr if proc.stderr is not None else "",
            }
            success = True
            error = None
            reason_code = None
        except (ValueError, TypeError) as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.invalid_input"
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.execution_error"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(
            success=success,
            output=result,
            error=error,
            latency_ms=latency_ms,
            reason_code=reason_code,
            stage=str(stage) if stage is not None else None,
        )


class EvidencePlugin(Plugin):
    """Stores/returns evidence objects for later inspection."""

    def __init__(self) -> None:
        self.name = "evidence"

    def execute(self, **kwargs: Any) -> PluginResult:
        started = time.perf_counter()
        stage = kwargs.get("stage")
        try:
            items = kwargs.get("items")
            if not isinstance(items, list):
                raise TypeError("items must be a list")
            result = {"items": items}
            success = True
            error = None
            reason_code = None
        except (ValueError, TypeError) as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.invalid_input"
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
            reason_code = "PLUGIN.execution_error"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(
            success=success,
            output=result,
            error=error,
            latency_ms=latency_ms,
            reason_code=reason_code,
            stage=str(stage) if stage is not None else None,
        )


def safe_execute_plugin(*, plugin: Plugin, timeout_ms: Optional[int], stage: Optional[str] = None, **kwargs: Any) -> PluginResult:
    """Execute a plugin with best-effort timeout + exception containment.

    - Passes stage into the plugin call (plugins must accept **kwargs).
    - Normalizes timeout/crash into PLUGIN-CONTRACT reason codes.
    """

    def _run() -> PluginResult:
        return plugin.execute(stage=stage, **kwargs)

    res = safe_call(fn=_run, timeout_ms=timeout_ms)
    if res.ok and isinstance(res.value, PluginResult):
        pr = res.value
        # override latency with measured (outer) time for consistency
        pr.latency_ms = res.latency_ms  # type: ignore[misc]
        # ensure stage is recorded
        if stage is not None:
            pr.stage = str(stage)  # type: ignore[misc]
        return pr

    if res.timed_out:
        return PluginResult(
            success=False,
            output=None,
            error="TIMEOUT",
            latency_ms=res.latency_ms,
            reason_code="PLUGIN.timeout",
            stage=str(stage) if stage is not None else None,
        )

    return PluginResult(
        success=False,
        output=None,
        error=res.error or "UNKNOWN_ERROR",
        latency_ms=res.latency_ms,
        reason_code="SYSTEM.unexpected_exception",
        stage=str(stage) if stage is not None else None,
    )
