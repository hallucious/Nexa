from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.models.decision_models import Decision, GateResult
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.contracts.standard_spec import standard_spec


def make_pass_gate(message: str):
    def _exec(ctx: GateContext) -> GateResult:
        return GateResult(
            decision=Decision.PASS,
            message=message,
            outputs={},
        )

    return _exec


def make_info_gate(message: str):
    # NOTE: kept as Decision.PASS for backward compatibility with existing tests/callers.
    def _exec(ctx: GateContext) -> GateResult:
        return GateResult(
            decision=Decision.PASS,
            message=message,
            outputs={},
        )

    return _exec


def make_contract_pass_gate(gate_prefix: str, message: str):
    """Mock gate that ALWAYS writes standard artifacts and PASS."""

    spec = standard_spec(gate_prefix)

    def _exec(ctx: GateContext) -> GateResult:
        run_dir = Path(ctx.run_dir)

        decision_md = f"# {gate_prefix} DECISION\n\n{message}\n"
        output_json: Dict[str, Any] = {"result": "pass", "gate": gate_prefix}
        meta_json: Dict[str, Any] = {
            "gate": gate_prefix,
            "decision": "PASS",
            "at": now_seoul().isoformat(),
            "attempt": getattr(getattr(ctx, "meta", None), "attempts", {}).get(gate_prefix, 1)
            if getattr(ctx, "meta", None) is not None
            else 1,
        }

        paths = {
            f"{gate_prefix}_DECISION.md": run_dir / f"{gate_prefix}_DECISION.md",
            f"{gate_prefix}_OUTPUT.json": run_dir / f"{gate_prefix}_OUTPUT.json",
            f"{gate_prefix}_META.json": run_dir / f"{gate_prefix}_META.json",
        }

        paths[f"{gate_prefix}_DECISION.md"].write_text(decision_md, encoding="utf-8")
        paths[f"{gate_prefix}_OUTPUT.json"].write_text(
            json.dumps(output_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        paths[f"{gate_prefix}_META.json"].write_text(
            json.dumps(meta_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        outputs = {name: str(path.name) for name, path in paths.items()}

        # validate contract
        spec.validate(outputs)

        return GateResult(
            decision=Decision.PASS,
            message=message,
            outputs=outputs,
        )

    return _exec
