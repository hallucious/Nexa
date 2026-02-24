
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from src.models.decision_models import Decision
from src.pipeline.runner import GateContext
from src.artifacts.writer import ArtifactWriter
from src.utils.time import now_seoul


def stable_json_dumps(obj: Any, *, indent: int = 2) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=True)


def is_pytest() -> bool:
    return os.getenv("PYTEST_CURRENT_TEST") is not None


def read_text_file(path: Path, *, encoding: str = "utf-8") -> str:
    try:
        return Path(path).read_text(encoding=encoding)
    except FileNotFoundError:
        return ""


def read_json_file(path: Path, *, encoding: str = "utf-8") -> Any:
    try:
        raw = Path(path).read_text(encoding=encoding)
    except FileNotFoundError:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


@dataclass
class GateResult:
    decision: Decision
    message: str
    outputs: Dict[str, str]
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


def write_standard_artifacts(*args, **kwargs) -> Dict[str, str]:
    """Compatibility wrapper delegating to ArtifactWriter."""

    if args and kwargs:
        raise TypeError("write_standard_artifacts: do not mix positional and keyword arguments")

    if args:
        if len(args) != 5:
            raise TypeError(
                "write_standard_artifacts(positional) expects 5 args: gate_id, decision, decision_md, output_dict, ctx"
            )
        gate_id, decision, decision_md, output_dict, ctx = args
        return ArtifactWriter.write_standard_artifacts(
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
    meta_extra = kwargs.get("meta_extra")

    if output_dict is None and "output" in kwargs:
        output_dict = kwargs.get("output")

    if ctx is None or gate_id is None or decision is None or decision_md is None or output_dict is None:
        raise TypeError(
            "write_standard_artifacts(keyword) requires ctx, gate_id, decision, decision_md, and output_dict/output"
        )

    return ArtifactWriter.write_standard_artifacts(
        gate_id=str(gate_id),
        decision=decision,
        decision_md=str(decision_md),
        output_dict=output_dict,
        ctx=ctx,
        meta_extra=meta_extra,
    )
