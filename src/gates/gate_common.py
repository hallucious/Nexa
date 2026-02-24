from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional



def stable_json_dumps(obj: Any, *, indent: int = 2) -> str:
    """Deterministic JSON dump used by gates/tests."""
    return json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=True)

def is_pytest() -> bool:
    """Return True when running under pytest."""
    return os.getenv("PYTEST_CURRENT_TEST") is not None

def read_text_file(path: Path, *, encoding: str = "utf-8") -> str:
    """Read text file safely; returns empty string if missing."""
    try:
        return Path(path).read_text(encoding=encoding)
    except FileNotFoundError:
        return ""


def read_json_file(path: Path, *, encoding: str = "utf-8") -> Any:
    """Read JSON file safely.

    - Returns parsed JSON value on success
    - Returns {} if missing or invalid JSON
    """
    try:
        raw = Path(path).read_text(encoding=encoding)
    except FileNotFoundError:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


from src.models.decision_models import Decision
from src.pipeline.contracts import standard_spec
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul


@dataclass
class GateResult:
    """Standard return type for gates."""

    decision: Decision
    message: str
    outputs: Dict[str, str]
    # Runner may attach additional metadata post-hoc.
    meta: Dict[str, Any] = field(default_factory=dict)


def format_standard_decision_md(
    gate_id: str,
    title: str,
    decision: Decision,
    summary: str,
    inputs: Optional[Mapping[str, Any]] = None,
    outputs: Optional[Mapping[str, Any]] = None,
    notes: Optional[List[str]] = None,
) -> str:
    """Minimal, stable markdown formatter used by multiple gates."""
    lines: List[str] = []
    lines.append(f"# {gate_id} {title}".strip())
    lines.append("")
    lines.append(f"Decision: {decision.value}")
    lines.append("")
    if summary:
        lines.append("## Summary")
        lines.append(str(summary).strip())
        lines.append("")
    if inputs is not None:
        lines.append("## Inputs")
        if len(inputs) == 0:
            lines.append("- (none)")
        else:
            for k, v in inputs.items():
                lines.append(f"- {k}: {v}")
        lines.append("")
    if outputs is not None:
        lines.append("## Outputs")
        if len(outputs) == 0:
            lines.append("- (none)")
        else:
            for k, v in outputs.items():
                lines.append(f"- {k}: {v}")
        lines.append("")
    if notes:
        lines.append("## Notes")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_standard_artifacts_core(
    gate_id: str,
    decision: Decision,
    decision_md: str,
    output_dict: dict,
    ctx: GateContext,
) -> Dict[str, str]:
    """Canonical writer: writes per-gate DECISION/OUTPUT/META and validates."""
    run_dir = Path(ctx.run_dir).resolve()

    decision_path = run_dir / f"{gate_id}_DECISION.md"
    output_path = run_dir / f"{gate_id}_OUTPUT.json"
    meta_path = run_dir / f"{gate_id}_META.json"

    decision_path.write_text(decision_md, encoding="utf-8")
    output_path.write_text(json.dumps(output_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "gate": gate_id,
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get(gate_id, 1),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = {
        f"{gate_id}_DECISION.md": f"{gate_id}_DECISION.md",
        f"{gate_id}_OUTPUT.json": f"{gate_id}_OUTPUT.json",
        f"{gate_id}_META.json": f"{gate_id}_META.json",
    }

    # Contract validation
    standard_spec(gate_id).validate(outputs)

    return outputs


def write_standard_artifacts(*args, **kwargs) -> Dict[str, str]:
    """Compatibility wrapper.

    Supported call styles:
      1) Legacy positional:
         write_standard_artifacts(gate_id, decision, decision_md, output_dict, ctx)

      2) Keyword style (used by some newer gates):
         write_standard_artifacts(ctx=..., gate_id=..., decision=..., decision_md=..., output_dict=...)
         - accepts output=... as alias of output_dict
    """
    if args and kwargs:
        raise TypeError("write_standard_artifacts: do not mix positional and keyword arguments")

    if args:
        if len(args) != 5:
            raise TypeError(
                "write_standard_artifacts(positional) expects 5 args: gate_id, decision, decision_md, output_dict, ctx"
            )
        gate_id, decision, decision_md, output_dict, ctx = args
        return _write_standard_artifacts_core(
            gate_id=str(gate_id),
            decision=decision,
            decision_md=str(decision_md),
            output_dict=output_dict,
            ctx=ctx,
        )

    ctx = kwargs.get("ctx")
    gate_id = kwargs.get("gate_id")
    decision = kwargs.get("decision")
    decision_md = kwargs.get("decision_md")
    output_dict = kwargs.get("output_dict")
    if output_dict is None and "output" in kwargs:
        output_dict = kwargs.get("output")

    if ctx is None or gate_id is None or decision is None or decision_md is None or output_dict is None:
        raise TypeError(
            "write_standard_artifacts(keyword) requires ctx, gate_id, decision, decision_md, and output_dict/output"
        )

    return _write_standard_artifacts_core(
        gate_id=str(gate_id),
        decision=decision,
        decision_md=str(decision_md),
        output_dict=output_dict,
        ctx=ctx,
    )
