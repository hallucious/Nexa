from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul


# -----------------------------
# Helpers
# -----------------------------
def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _truncate(s: str, max_chars: int = 4000) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "\n...[truncated]...\n"


def _find_repo_root(run_dir: Path) -> Path:
    """
    Locate repo root by walking upward until we see expected folders.
    Designed for both real runs/ and pytest tmp repos.
    """
    cur = run_dir.resolve()
    for _ in range(12):
        if (cur / "src").exists() and (cur / "tests").exists():
            return cur
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    # fallback: parent of run_dir (works for tmp repo layout in tests)
    return run_dir.parent.parent if run_dir.parent.name == "runs" else run_dir.parent


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _load_execution_command_from_g4_output(run_dir: Path) -> Optional[List[str]]:
    """
    Preferred: structured command from G4_OUTPUT.json, if present.

    We support multiple possible keys to stay backward/forward compatible:
      - execution_command: ["python", "-m", "pytest", "-q"]
      - execution_plan_cmd: same
      - g5_command: same
    """
    p = run_dir / "G4_OUTPUT.json"
    if not p.exists():
        return None

    try:
        out = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

    for key in ("execution_command", "execution_plan_cmd", "g5_command"):
        cmd = out.get(key)
        if isinstance(cmd, list) and all(isinstance(x, str) for x in cmd):
            return cmd

    return None


def _load_execution_command_from_g4_decision(run_dir: Path) -> Optional[List[str]]:
    """
    Fallback: parse G4_DECISION.md and extract the first line that looks like a pytest command.
    """
    p = run_dir / "G4_DECISION.md"
    if not p.exists():
        return None

    text = p.read_text(encoding="utf-8", errors="replace")
    # Look for: "python -m pytest -q" (allow extra args)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^python\s+-m\s+pytest(\s+.*)?$", line, flags=re.IGNORECASE):
            return shlex.split(line, posix=False)
        if re.match(r"^pytest(\s+.*)?$", line, flags=re.IGNORECASE):
            return shlex.split(line, posix=False)

    return None


def _choose_execution_command(run_dir: Path) -> List[str]:
    """
    Gate4 is responsible for producing clear execution instructions for Gate5.
    Gate5 will try, in order:
      1) structured command from G4_OUTPUT.json
      2) parse command from G4_DECISION.md
      3) default to: python -m pytest -q
    """
    cmd = _load_execution_command_from_g4_output(run_dir)
    if cmd:
        return cmd

    cmd = _load_execution_command_from_g4_decision(run_dir)
    if cmd:
        return cmd

    return ["python", "-m", "pytest", "-q"]


def _format_decision_md(
    *,
    decision: Decision,
    repo_root: Path,
    cmd: List[str],
    returncode: Optional[int],
    timeout: bool,
    duration_sec: float,
    stdout: str,
    stderr: str,
    notes: str,
) -> str:
    rc = "TIMEOUT" if timeout else str(returncode)
    return (
        "# G5 IMPLEMENT & TEST DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Command\n"
        f"- cwd: {repo_root}\n"
        f"- cmd: {' '.join(cmd)}\n\n"
        "## Result\n"
        f"- returncode: {rc}\n"
        f"- timeout: {timeout}\n"
        f"- duration_sec: {duration_sec:.2f}\n\n"
        "## Output (truncated)\n"
        "### stdout\n"
        "```text\n"
        f"{_truncate(stdout)}\n"
        "```\n\n"
        "### stderr\n"
        "```text\n"
        f"{_truncate(stderr)}\n"
        "```\n\n"
        "## Notes\n"
        f"{notes}\n"
    )


# -----------------------------
# Gate5
# -----------------------------
def gate_g5_implement_and_test(ctx: GateContext) -> GateResult:
    """
    Gate5 = local implement/test executor (deterministic, no network requirements).

    Responsibilities:
      - Execute the command that Gate4 produced as "G5 execution instructions"
      - Record artifacts (decision/meta/output)
      - PASS only when tests succeed (rc=0)
      - FAIL on nonzero rc or timeout
    """
    run_dir = Path(ctx.run_dir).resolve()
    repo_root = _find_repo_root(run_dir)

    cmd = _choose_execution_command(run_dir)

    # Parallel-run hardening: isolate pytest base temp and cache per run.
    # This avoids cross-process contention when multiple pipelines run simultaneously.
    if "pytest" in " ".join(cmd).lower():
        basetemp = str(run_dir / ".pytest_basetemp")
        if "--basetemp" not in cmd:
            cmd += ["--basetemp", basetemp]
        # Explicitly disable cache provider; we already set PYTEST_CACHE_DIR, but this makes it robust.
        if "-p" not in cmd and "no:cacheprovider" not in " ".join(cmd):
            cmd += ["-p", "no:cacheprovider"]

    # Parallel-run hardening: isolate pytest cache per run to avoid cross-process contention.
    # (pytest otherwise writes .pytest_cache under repo root, which can race under concurrency.)
    env = os.environ.copy()
    # Reduce influence of user/global pytest plugins (can vary per machine).
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTEST_CACHE_DIR", str(run_dir / ".pytest_cache"))

    timeout_sec = _env_int("HAI_PYTEST_TIMEOUT_SEC", 120)

    started = now_seoul()
    timed_out = False
    rc: Optional[int] = None
    out_s = ""
    err_s = ""

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_sec,
        )
        rc = proc.returncode
        out_s = proc.stdout or ""
        err_s = proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        out_s = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err_s = (e.stderr or "") if isinstance(e.stderr, str) else ""
        err_s = (err_s + "\n" if err_s else "") + f"TIMEOUT: command exceeded {timeout_sec}s\n"

    duration = (now_seoul() - started).total_seconds()

    if (not timed_out) and rc == 0:
        decision = Decision.PASS
        msg = "Tests passed."
        notes = "- Tests completed successfully.\n- Gate5 is local-only and deterministic."
    else:
        decision = Decision.FAIL
        if timed_out:
            msg = f"Tests timed out after {timeout_sec}s."
        else:
            msg = f"Tests failed (rc={rc})."
        notes = (
            "- Gate5 must be deterministic: avoid network calls during tests.\n"
            "- If failures are intermittent, isolate nondeterminism (randomness, timing, external services).\n"
            "- Re-run locally with the same command until stable."
        )

    decision_md = _format_decision_md(
        decision=decision,
        repo_root=repo_root,
        cmd=cmd,
        returncode=rc,
        timeout=timed_out,
        duration_sec=duration,
        stdout=out_s,
        stderr=err_s,
        notes=notes,
    )

    meta = {
        "gate": "G5",
        "created_at": now_seoul().isoformat(),
        "cwd": str(repo_root),
        "cmd": cmd,
        "timeout_sec": timeout_sec,
        "timeout": timed_out,
        "returncode": rc,
        "duration_sec": duration,
    }

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
        "inputs": {
            "G4_OUTPUT.json": "G4_OUTPUT.json" if (run_dir / "G4_OUTPUT.json").exists() else None,
            "G4_DECISION.md": "G4_DECISION.md" if (run_dir / "G4_DECISION.md").exists() else None,
        },
    }

    (run_dir / "G5_DECISION.md").write_text(decision_md, encoding="utf-8")
    _write_json(run_dir / "G5_META.json", meta)
    _write_json(run_dir / "G5_OUTPUT.json", output)

    return GateResult(
        decision=decision,
        message=msg,
        outputs={
            "G5_DECISION.md": "G5_DECISION.md",
            "G5_OUTPUT.json": "G5_OUTPUT.json",
            "G5_META.json": "G5_META.json",
        },
        meta=meta,
    )
