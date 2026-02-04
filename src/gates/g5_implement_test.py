from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_repo_root(run_dir: Path) -> Path:
    """
    Repo root locator for real runs.
    We accept a folder as repo root if it contains:
      - src/ and tests/ and runs/
    Fallback: parent of run_dir.
    """
    p = run_dir.resolve()
    for parent in [p] + list(p.parents):
        if (parent / "src").exists() and (parent / "tests").exists() and (parent / "runs").exists():
            return parent
    return run_dir.parent


def _truncate(s: str, limit: int = 20000) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + "\n...[truncated]...\n"


def gate_g5_implement_and_test(ctx: GateContext) -> GateResult:
    """
    Step 8 (stub):
    - No code generation yet.
    - Executes test suite and captures results.
    - Produces standard artifacts.

    Decision:
    - PASS if tests return code == 0
    - FAIL otherwise (including timeout)
    """
    run_dir = Path(ctx.run_dir).resolve()
    repo_root = _find_repo_root(run_dir)

    # Optional inputs (for traceability)
    g1 = (run_dir / "G1_OUTPUT.json").exists()
    g2 = (run_dir / "G2_OUTPUT.json").exists()
    g3 = (run_dir / "G3_OUTPUT.json").exists()
    g4 = (run_dir / "G4_OUTPUT.json").exists()

    cmd = ["python", "-m", "pytest", "-q"]
    started = time.time()

    timeout_sec = 60
    timed_out = False
    rc: Optional[int] = None
    stdout = ""
    stderr = ""

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        rc = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = 124
        stdout = (e.stdout or "") if isinstance(e.stdout, str) else ""
        stderr = (e.stderr or "") if isinstance(e.stderr, str) else ""
        stderr += f"\nTIMEOUT: pytest exceeded {timeout_sec}s\n"

    duration_sec = round(time.time() - started, 3)

    decision = Decision.PASS if (rc == 0 and not timed_out) else Decision.FAIL

    # Artifacts
    decision_md = (
        "# G5 IMPLEMENT & TEST DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        "## Command\n"
        f"- cwd: {repo_root}\n"
        f"- cmd: {' '.join(cmd)}\n\n"
        "## Result\n"
        f"- returncode: {rc}\n"
        f"- timeout: {timed_out}\n"
        f"- duration_sec: {duration_sec}\n\n"
        "## Output (truncated)\n"
        "### stdout\n"
        "```text\n"
        f"{_truncate(stdout)}\n"
        "```\n\n"
        "### stderr\n"
        "```text\n"
        f"{_truncate(stderr)}\n"
        "```\n"
    )
    (run_dir / "G5_DECISION.md").write_text(decision_md, encoding="utf-8")

    output = {
        "gate": "G5",
        "mode": "implement_and_test_stub",
        "repo_root": str(repo_root),
        "command": {"cwd": str(repo_root), "cmd": cmd, "timeout_sec": timeout_sec},
        "result": {
            "returncode": rc,
            "timeout": timed_out,
            "duration_sec": duration_sec,
        },
        "captured": {
            "stdout": _truncate(stdout),
            "stderr": _truncate(stderr),
        },
        "inputs_present": {
            "G1_OUTPUT.json": g1,
            "G2_OUTPUT.json": g2,
            "G3_OUTPUT.json": g3,
            "G4_OUTPUT.json": g4,
        },
        "notes": [
            "No code generation performed in this stub.",
            "Next step will add an 'implementation plan' artifact and optional LLM plugin.",
        ],
    }
    _write_json(run_dir / "G5_OUTPUT.json", output)

    meta = {
        "gate": "G5",
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get("G5", 1),
    }
    _write_json(run_dir / "G5_META.json", meta)

    outputs = {
        "G5_DECISION.md": "G5_DECISION.md",
        "G5_OUTPUT.json": "G5_OUTPUT.json",
        "G5_META.json": "G5_META.json",
    }
    standard_spec("G5").validate(outputs)

    return GateResult(
        decision=decision,
        message="Implement & test completed (stub)",
        outputs=outputs,
        meta={"returncode": rc, "timeout": timed_out, "duration_sec": duration_sec},
    )
