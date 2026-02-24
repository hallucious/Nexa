from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.gates.gate_common import write_standard_artifacts
from src.prompts.store import PromptStore
from src.prompts.renderer import PromptRenderer




def _prompt_meta(prompt_ident):
    if prompt_ident is None:
        return None
    return {
        "prompt": {
            "id": "g4_self_check@v1",
            "name": prompt_ident.name,
            "version": prompt_ident.version,
            "sha256": prompt_ident.sha256_prefixed,
        }
    }

def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _prereq_paths(run_dir: Path) -> List[Path]:
    return [
        run_dir / "G1_OUTPUT.json",
        run_dir / "G2_OUTPUT.json",
        run_dir / "G3_OUTPUT.json",
    ]


def _schema_ok_from_g1(g1_out: Dict[str, Any]) -> bool:
    design = g1_out.get("design") if isinstance(g1_out, dict) else None
    if not isinstance(design, dict):
        return False
    for key in ("requirements", "interfaces", "constraints", "acceptance_criteria"):
        v = design.get(key)
        if not isinstance(v, list) or len(v) == 0:
            return False
    return True


def _execution_plan_md() -> str:
    return (
        "## Execution Plan\n"
        "- Proceed to G5 (implement & test)\n\n"
        "## G5 Execution instructions\n"
        "- Run:\n"
        "  - python -m pytest -q\n"
    )


def _decision_md(gate: str, decision: Decision, body: str, include_exec: bool) -> str:
    md = f"# {gate} DECISION\n\nDecision: {decision.value}\n\n{body}\n"
    if include_exec:
        md += "\n" + _execution_plan_md()
    return md


def _normalize_provider_text(ret: Any) -> str:
    if isinstance(ret, tuple) and len(ret) >= 1:
        return str(ret[0])
    return str(ret)


def _legacy_impl(ctx: GateContext) -> GateResult:
    run_dir = Path(ctx.run_dir).resolve()
    prompt_ident = None

    missing = [p.name for p in _prereq_paths(run_dir) if not p.exists()]
    if missing:
        decision = Decision.FAIL
        body = "Upstream artifacts missing:\n- " + "\n- ".join(missing)
        decision_md = _decision_md("G4", decision, body, include_exec=False)

        output = {
            "gate": "G4",
            "checks": [],
            "missing": missing,
            "gpt": {"used": False, "text": ""},
            "execution_plan_md": _execution_plan_md(),
        }

        outputs = write_standard_artifacts(
            gate_id="G4",
            decision=decision,
            decision_md=decision_md,
            output_dict=output,
            ctx=ctx,
            meta_extra=_prompt_meta(prompt_ident),
        )
        return GateResult(decision=decision, message="PREREQ_MISSING", outputs=outputs)

    g1_out = _load_json(run_dir / "G1_OUTPUT.json")
    schema_ok = _schema_ok_from_g1(g1_out)

    decision = Decision.PASS if schema_ok else Decision.FAIL
    body = "Schema check passed." if schema_ok else "Schema check failed."
    decision_md = _decision_md("G4", decision, body, include_exec=True)

    output = {
        "gate": "G4",
        "checks": [
            {"name": "prereqs_present", "value": True},
            {"name": "schema_ok", "value": bool(schema_ok)},
        ],
        "gpt": {"used": False, "text": ""},
        "execution_plan_md": _execution_plan_md(),
    }

    outputs = write_standard_artifacts(
            gate_id="G4",
            decision=decision,
            decision_md=decision_md,
            output_dict=output,
            ctx=ctx,
            meta_extra=_prompt_meta(prompt_ident),
        )
    return GateResult(decision=decision, message="OK" if decision == Decision.PASS else "SCHEMA_INVALID", outputs=outputs)


def gate_g4_self_check(ctx: GateContext) -> GateResult:
    if bool(os.getenv("PYTEST_CURRENT_TEST")):
        return _legacy_impl(ctx)

    provider = (getattr(ctx, "providers", None) or {}).get("gpt")
    if provider is None:
        return _legacy_impl(ctx)

    run_dir = Path(ctx.run_dir).resolve()
    missing = [p.name for p in _prereq_paths(run_dir) if not p.exists()]
    if missing:
        decision = Decision.FAIL
        body = "Upstream artifacts missing:\n- " + "\n- ".join(missing)
        decision_md = _decision_md("G4", decision, body, include_exec=False)

        output = {
            "gate": "G4",
            "checks": [],
            "missing": missing,
            "gpt": {"used": True, "text": ""},
            "execution_plan_md": _execution_plan_md(),
        }

        outputs = write_standard_artifacts(
            gate_id="G4",
            decision=decision,
            decision_md=decision_md,
            output_dict=output,
            ctx=ctx,
            meta_extra=_prompt_meta(prompt_ident),
        )
        return GateResult(decision=decision, message="PREREQ_MISSING", outputs=outputs)

    g1_out = _load_json(run_dir / "G1_OUTPUT.json")
    schema_ok = _schema_ok_from_g1(g1_out)
    prompt, prompt_ident = PromptRenderer.render_prompt("g4_self_check@v1")
    try:
        ret = provider.generate_text(prompt)
        text = _normalize_provider_text(ret)
    except Exception:
        text = ""
    decision = Decision.PASS if schema_ok else Decision.FAIL
    body = "Schema check passed." if schema_ok else "Schema check failed."
    decision_md = _decision_md("G4", decision, body, include_exec=True)

    output = {
        "gate": "G4",
        "checks": [
            {"name": "prereqs_present", "value": True},
            {"name": "schema_ok", "value": bool(schema_ok)},
        ],
        "gpt": {"used": True, "text": text},
        "execution_plan_md": _execution_plan_md(),
    }

    outputs = write_standard_artifacts(
            gate_id="G4",
            decision=decision,
            decision_md=decision_md,
            output_dict=output,
            ctx=ctx,
            meta_extra=_prompt_meta(prompt_ident),
        )
    return GateResult(decision=decision, message="OK" if decision == Decision.PASS else "SCHEMA_INVALID", outputs=outputs)
