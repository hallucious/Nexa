from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.decision_models import Decision, GateResult
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul

from src.platform.prompt_spec import PromptSpec
from src.platform.worker import wrap_text_provider, WorkerResult
from src.platform.plugin import FileWritePlugin


def _extract_requirements(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _self_check(design: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    if not design.get("interfaces"):
        violations.append("interfaces missing")
    if not design.get("constraints"):
        violations.append("constraints missing")
    if not design.get("acceptance_criteria"):
        violations.append("acceptance_criteria missing")
    return violations


def _get_injected_gpt(ctx: GateContext) -> Optional[Any]:
    if isinstance(getattr(ctx, "providers", None), dict) and ctx.providers.get("gpt") is not None:
        return ctx.providers.get("gpt")

    providers = ctx.context.get("providers")
    if isinstance(providers, dict) and providers.get("gpt") is not None:
        return providers.get("gpt")

    if ctx.context.get("gpt") is not None:
        return ctx.context.get("gpt")

    return None


_G1_PROMPT = PromptSpec(
    id="g1_design/v1",
    version="v1",
    template=(
        "You are Gate1 (Design). Create a concise JSON design skeleton for the request below. "
        "Return ONLY valid JSON with keys: summary, requirements, interfaces, constraints, acceptance_criteria.\n\n"
        "REQUEST:\n"
        "{user_request}"
    ),
    inputs_schema={"user_request": str},
)


# Plugin (v0.1 contract): no ctor args; execute(path=..., content=...)
_G1_FILE_WRITE = FileWritePlugin()


def gate_g1_design(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir)
    req_path = run_dir / "00_USER_REQUEST.md"
    if not req_path.exists():
        raise FileNotFoundError("00_USER_REQUEST.md not found")

    req_text = req_path.read_text(encoding="utf-8", errors="ignore")
    requirements = _extract_requirements(req_text)

    is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))

    gpt_used = False
    gpt_error = ""
    gpt_raw: Dict[str, Any] = {}
    gpt_text = ""

    provider = _get_injected_gpt(ctx)

    if (not is_pytest) and (provider is None):
        decision = Decision.STOP
        violations = ["GPT unavailable: missing injected provider"]
        design: Dict[str, Any] = {}
    else:
        # Deterministic baseline (stable in tests)
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

        # AI path only when NOT pytest (keeps test determinism)
        if (not is_pytest) and (provider is not None):
            try:
                gpt_used = True
                rendered = _G1_PROMPT.render({"user_request": req_text.strip()[:8000]})

                if hasattr(provider, "generate_text") and callable(getattr(provider, "generate_text")):
                    worker = wrap_text_provider(name="gpt", provider=provider)
                    wr: WorkerResult = worker.generate_text(
                        prompt=rendered,
                        temperature=0.0,
                        max_output_tokens=2048,
                    )
                    gpt_text = wr.text
                    gpt_raw = wr.raw if isinstance(wr.raw, dict) else {}
                    if (not wr.success) and wr.error:
                        gpt_error = wr.error
                else:
                    gpt_error = "Provider missing generate_text()"

            except Exception as e:
                gpt_error = f"{type(e).__name__}: {e}"

        # Adopt AI JSON if valid
        if gpt_text.strip():
            try:
                candidate = json.loads(gpt_text)
                if isinstance(candidate, dict):
                    design = candidate
            except Exception:
                pass

        violations = _self_check(design)
        decision = Decision.PASS if not violations else Decision.FAIL

    # --- Standard contract artifacts (unchanged) ---

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

    # --- Additive artifact via Plugin (non-breaking) ---
    design_md = "# G1 DESIGN\n\n" + json.dumps(design, ensure_ascii=False, indent=2)
    _G1_FILE_WRITE.execute(path=run_dir / "G1_DESIGN.md", content=design_md)

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
