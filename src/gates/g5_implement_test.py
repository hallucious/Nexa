from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.gates.gate_common import write_standard_artifacts
from src.utils.time import now_seoul
from src.policy.gate_policy import evaluate_g5


def _truncate(s: str, max_chars: int = 4000) -> str:
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "\n...[truncated]...\n"


def _find_repo_root(run_dir: Path) -> Path:
    cur = run_dir.resolve()
    for _ in range(12):
        if (cur / "src").exists() and (cur / "tests").exists():
            return cur
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return run_dir.parent.parent if run_dir.parent.name == "runs" else run_dir.parent


def _choose_execution_command() -> List[str]:
    return ["python", "-m", "pytest", "-q"]


def gate_g5_implement_and_test(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()
    repo_root = _find_repo_root(run_dir)

    cmd = _choose_execution_command()

    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTEST_CACHE_DIR", str(run_dir / ".pytest_cache"))

    timeout_sec = int(os.environ.get("HAI_PYTEST_TIMEOUT_SEC", "120") or 120)

    started = now_seoul()
    timed_out = False
    rc: Optional[int] = None
    out_s = ""
    err_s = ""

    try:
        exec_plugin = getattr(ctx, "plugins", {}).get("exec") if hasattr(ctx, "plugins") else None
        if exec_plugin is not None and hasattr(exec_plugin, "execute"):
            pr = exec_plugin.execute(cmd, cwd=str(repo_root), env=env, timeout_s=timeout_sec)
            if not getattr(pr, "success", False) or not getattr(pr, "output", None):
                raise RuntimeError(getattr(pr, "error", None) or "Execution plugin failed")
            rc = int(pr.output.get("returncode", 1))
            stdout = str(pr.output.get("stdout", ""))
            stderr = str(pr.output.get("stderr", ""))
        else:
            proc = subprocess.run(
                cmd,
                cwd=str(repo_root),
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_sec,
                check=False,
            )
            rc = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        out_s = stdout or ""
        err_s = stderr or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        out_s = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err_s = (e.stderr or "") if isinstance(e.stderr, str) else ""
        err_s = (err_s + "\n" if err_s else "") + f"TIMEOUT: command exceeded {timeout_sec}s\n"

    duration = (now_seoul() - started).total_seconds()

    policy = evaluate_g5(timed_out=timed_out, returncode=rc)
    decision = policy.decision
    msg = policy.message

    decision_md = (
        "# G5 IMPLEMENT & TEST DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Command\n"
        f"- cwd: {repo_root}\n"
        f"- cmd: {' '.join(cmd)}\n\n"
        "## Result\n"
        f"- returncode: {rc}\n"
        f"- timeout: {timed_out}\n"
        f"- duration_sec: {duration:.2f}\n"
    )

    output = {
        "gate": "G5",
        "decision": decision.value,
        "message": msg,
        "command": {"cwd": str(repo_root), "cmd": cmd},
        "result": {
            "timeout": timed_out,
            "timeout_sec": timeout_sec,
            "returncode": rc,
            "duration_sec": duration,
        },
        "stdout": _truncate(out_s),
        "stderr": _truncate(err_s),
    }

    outputs = write_standard_artifacts("G5", decision, decision_md, output, ctx)

    return GateResult(
        decision=decision,
        message=msg,
        outputs=outputs,
    )