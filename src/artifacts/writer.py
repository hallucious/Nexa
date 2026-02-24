
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from src.utils.time import now_seoul
from src.models.decision_models import Decision
from src.pipeline.runner import GateContext


class ArtifactWriter:
    """Artifact/IO Layer for standard gate outputs (pure I/O)."""

    @staticmethod
    def write_standard_artifacts(
        gate_id: str,
        decision: Decision,
        decision_md: str,
        output_dict: dict,
        ctx: GateContext,
    ) -> Dict[str, str]:

        run_dir = Path(ctx.run_dir).resolve()

        decision_path = run_dir / f"{gate_id}_DECISION.md"
        output_path = run_dir / f"{gate_id}_OUTPUT.json"
        meta_path = run_dir / f"{gate_id}_META.json"

        decision_path.write_text(decision_md, encoding="utf-8")
        output_path.write_text(
            json.dumps(output_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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

        return {
            f"{gate_id}_DECISION.md": f"{gate_id}_DECISION.md",
            f"{gate_id}_OUTPUT.json": f"{gate_id}_OUTPUT.json",
            f"{gate_id}_META.json": f"{gate_id}_META.json",
        }
