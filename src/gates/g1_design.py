from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from src.models.decision_models import GateResult, Decision
from src.pipeline.runner import GateContext
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


def _extract_requirements(text: str) -> List[str]:
    # 최소 구현: 문단 단위 분해
    return [line.strip() for line in text.splitlines() if line.strip()]


def _self_check(design: Dict) -> List[str]:
    """
    Returns list of violations. Empty list => PASS.
    """
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

    violations = _self_check(design)
    decision = Decision.PASS if not violations else Decision.FAIL

    # Write artifacts
    (run_dir / "G1_DECISION.md").write_text(
        "# G1 DESIGN DECISION\n\n"
        f"Decision: {decision.value}\n\n"
        f"Violations: {violations if violations else 'None'}\n",
        encoding="utf-8",
    )

    (run_dir / "G1_OUTPUT.json").write_text(
        json.dumps(design, ensure_ascii=False, indent=2),
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

    # contract validate
    standard_spec("G1").validate(outputs)

    return GateResult(
        decision=decision,
        message="Design skeleton generated",
        outputs=outputs,
    )
