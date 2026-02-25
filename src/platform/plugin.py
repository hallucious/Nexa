from __future__ import annotations

import time
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class PluginResult:
    success: bool
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    latency_ms: int


class Plugin:
    name: str

    def execute(self, **kwargs) -> PluginResult:
        raise NotImplementedError


class DummyEchoPlugin(Plugin):
    """Minimal v0.1 plugin for contract verification only."""

    def __init__(self) -> None:
        self.name = "dummy_echo"

    def execute(self, **kwargs) -> PluginResult:
        started = time.perf_counter()
        try:
            result = {"echo": dict(kwargs)}
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(success=success, output=result, error=error, latency_ms=latency_ms)


class FileWritePlugin(Plugin):
    """Write text content to a file (v0.1)."""

    def __init__(self) -> None:
        self.name = "file_write"

    def execute(self, **kwargs) -> PluginResult:
        """
        Required kwargs:
          - path: str | Path
          - content: str
        Optional:
          - encoding: str (default: utf-8)
          - mkdirs: bool (default: True)  # create parent dirs
          - overwrite: bool (default: True)
        """
        started = time.perf_counter()
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
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"

        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(success=success, output=result, error=error, latency_ms=latency_ms)

class ExecutionPlugin(Plugin):
    """Executes a subprocess command and returns captured stdout/stderr.

    Purpose: make gate execution side-effects injectable/mocked in tests and swappable in future.
    """

    def __init__(self) -> None:
        self.name = "exec"

    def execute(
        self,
        cmd: Any,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_s: Optional[float] = None,
        shell: bool = False,
        text_mode: bool = True,
    ) -> PluginResult:
        started = time.perf_counter()
        try:
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
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(success=success, output=result, error=error, latency_ms=latency_ms)


class EvidencePlugin(Plugin):
    """Stores/returns evidence objects for later inspection.

    This is intentionally minimal (v0.1): it doesn't fetch the web. Gates can pass
    structured evidence items, and the plugin returns them unchanged.
    """

    def __init__(self) -> None:
        self.name = "evidence"

    def execute(self, items: Any) -> PluginResult:
        started = time.perf_counter()
        try:
            if not isinstance(items, list):
                raise TypeError("items must be a list")
            result = {"items": items}
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = f"{type(e).__name__}: {e}"
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PluginResult(success=success, output=result, error=error, latency_ms=latency_ms)
