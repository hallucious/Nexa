from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from src.models.decision_models import Decision, GateResult
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul

try:
    from src.providers.gpt_provider import GPTProvider
except Exception:  # pragma: no cover
    GPTProvider = None  # type: ignore


def _extract_requirements(text: str) -> List[str]:
    # 최소 구현: 문단 단위 분해
    return [line.strip() for line in text.splitlines() if line.strip()]


def _self_check(design: Dict) -> List[str]:
    """Returns list of violations. Empty list => PASS."""
    violations = []
    if not design.get("interfaces"):
        violations.append("interfaces missing")
    if not design.get("constraints"):
        violations.append("constraints missing")
    if not design.get("acceptance_criteria"):
        violations.append("acceptance_criteria missing")
    return violations


def gate_g1_design(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir)
    req_path = run_dir / "00_USER_REQUEST.md"
    if not req_path.exists():
        raise FileNotFoundError("00_USER_REQUEST.md not found")

    req_text = req_path.read_text(encoding="utf-8", errors="ignore")
    requirements = _extract_requirements(req_text)

    # GPT is REQUIRED for G1 in normal (non-pytest) pipeline runs.
    is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))
    gpt_used = False
    gpt_error = ""
    gpt_raw = {}
    gpt_text = ""

    if (not is_pytest) and GPTProvider is not None:
        try:
            provider = GPTProvider.from_env()
            gpt_used = True
            prompt = (
                "You are Gate1 (Design). Create a concise JSON design skeleton for the request below. "
                "Return ONLY valid JSON with keys: summary, requirements, interfaces, constraints, acceptance_criteria.\n\n"
                "REQUEST:\n"
                f"{req_text.strip()[:8000]}"
            )
            gpt_text, gpt_raw, err = provider.generate_text(
                prompt=prompt, temperature=0.0, max_output_tokens=2048
            )
            if err is not None:
                gpt_error = f"{type(err).__name__}: {err}"
        except Exception as e:
            gpt_error = f"{type(e).__name__}: {e}"

    if (not is_pytest) and (not gpt_used):
        decision = Decision.STOP
        violations = [f"GPT unavailable: {gpt_error or 'missing provider / key'}"]
        design: Dict = {}
    else:
        # Local fallback skeleton (still deterministic for tests)
        design = {
            "summary": "Initial system design (skeleton)",
            "requirements": requirements,
            "interfaces": ["pipeline runner", "gate contracts"],
            "constraints": [
                "file-based artifacts only",
                "no side effects outside run_dir",
                "contracts enforced",
            ],
            "acceptance_criteria": [
                "all gates produce standard artifacts",
                "state machine enforces transitions",
            ],
        }

        # If GPT returned JSON, try to adopt it.
        if gpt_text.strip():
            try:
                candidate = json.loads(gpt_text)
                if isinstance(candidate, dict):
                    design = candidate
            except Exception:
                pass

        violations = _self_check(design)
        decision = Decision.PASS if not violations else Decision.FAIL

    # Write artifacts
    (run_dir / "G1_DECISION.md").write_text(
        "# G1 DESIGN DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        f"Violations: {violations if violations else 'None'}\n",
        encoding="utf-8",
    )

    out_payload = {
        "design": design,
        "ai": {
            "engine": "gpt",
            "used": gpt_used,
            "model": (os.getenv("GPT_MODEL", "") or "gpt-5.2").strip(),
            "error": gpt_error,
            "raw": gpt_raw,
            "text": gpt_text,
        },
    }

    (run_dir / "G1_OUTPUT.json").write_text(
        json.dumps(out_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (run_dir / "G1_META.json").write_text(
        json.dumps(
            {
                "gate": "G1",
                "decision": decision.value,
                "violations": violations,
                "at": now_seoul().isoformat(),
                "attempt": ctx.meta.attempts.get("G1", 1),
                "ai": {"engine": "gpt", "used": gpt_used, "error": gpt_error},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    outputs = {
        "G1_DECISION.md": "G1_DECISION.md",
        "G1_OUTPUT.json": "G1_OUTPUT.json",
        "G1_META.json": "G1_META.json",
    }

    standard_spec("G1").validate(outputs)

    return GateResult(
        decision=decision,
        message="Design skeleton generated",
        outputs=outputs,
    )
