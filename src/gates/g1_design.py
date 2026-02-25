
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.prompts.store import PromptStore
from src.prompts.renderer import PromptRenderer
from src.pipeline.contracts import standard_spec

from src.platform.g1_design_plugin import run_g1_design_plugin


def _extract_requirements(text: str):
    return [line.strip() for line in text.splitlines() if line.strip()]


def _self_check(design: Dict[str, Any]):
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

    is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))
    provider = (ctx.providers or {}).get("gpt")

    ai = run_g1_design_plugin(request_text=req_text, provider=provider, is_pytest=is_pytest)
    gpt_used = ai.used
    gpt_error = ai.error
    gpt_text = ai.text
    prompt_ident = ai.prompt_ident

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

    if gpt_text.strip():
        try:
            candidate = json.loads(gpt_text)
            if isinstance(candidate, dict):
                design = candidate
        except Exception:
            pass

    violations = _self_check(design)
    decision = Decision.PASS if not violations else Decision.FAIL

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
            "error": gpt_error,
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
                "prompt": (
                    {
                        "id": "g1_design@v1",
                        "name": prompt_ident.name,
                        "version": prompt_ident.version,
                        "sha256": prompt_ident.sha256_prefixed,
                    }
                    if prompt_ident is not None else None
                ),
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
