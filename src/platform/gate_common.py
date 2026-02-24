
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.models.decision_models import Decision
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul
from src.pipeline.runner import GateContext


def write_standard_artifacts(
    gate_id: str,
    decision: Decision,
    decision_md: str,
    output_dict: dict,
    ctx: GateContext,
) -> Dict[str, str]:
    """
    Common artifact writer for Gates.

    Responsibilities:
    - Write DECISION.md
    - Write OUTPUT.json
    - Write META.json
    - Validate via standard_spec
    - Return outputs mapping

    IMPORTANT:
    - Does NOT change decision semantics.
    - Does NOT mutate ctx.meta except reading attempts.
    - Pure structural utility.
    """

    run_dir = Path(ctx.run_dir).resolve()

    decision_path = run_dir / f"{gate_id}_DECISION.md"
    output_path = run_dir / f"{gate_id}_OUTPUT.json"
    meta_path = run_dir / f"{gate_id}_META.json"

    # Write decision markdown
    decision_path.write_text(decision_md, encoding="utf-8")

    # Write output JSON
    output_path.write_text(
        json.dumps(output_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Write meta JSON (standardized minimal fields)
    meta = {
        "gate": gate_id,
        "decision": decision.value,
        "at": now_seoul().isoformat(),
        "attempt": ctx.meta.attempts.get(gate_id, 1),
    }

    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    outputs = {
        f"{gate_id}_DECISION.md": f"{gate_id}_DECISION.md",
        f"{gate_id}_OUTPUT.json": f"{gate_id}_OUTPUT.json",
        f"{gate_id}_META.json": f"{gate_id}_META.json",
    }

    standard_spec(gate_id).validate(outputs)

    return outputs
