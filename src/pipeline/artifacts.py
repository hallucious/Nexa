from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from src.pipeline.state import RunMeta
from src.utils.time import make_run_id


class Artifacts:
    def __init__(self, repo_root: Path, run_id: str):
        self.repo_root = repo_root
        self.run_id = run_id
        self.run_dir = repo_root / "runs" / run_id

    @staticmethod
    def create_new(repo_root: Path, run_id: Optional[str] = None) -> "Artifacts":
        rid = run_id or make_run_id()
        a = Artifacts(repo_root=repo_root, run_id=rid)
        a.run_dir.mkdir(parents=True, exist_ok=False)
        return a

    def path(self, artifact_filename: str) -> Path:
        return self.run_dir / artifact_filename

    def write_text(self, artifact_filename: str, content: str) -> Path:
        p = self.path(artifact_filename)
        p.write_text(content, encoding="utf-8")
        return p

    def write_json(self, artifact_filename: str, data: dict) -> Path:
        p = self.path(artifact_filename)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    @staticmethod
    def _build_safe_mode_summary(meta: RunMeta) -> Optional[Dict[str, Any]]:
        # Runner populates `meta.safe_mode_metrics` (dict) when SAFE_MODE triggers occur.
        metrics = getattr(meta, "safe_mode_metrics", None)
        if not isinstance(metrics, dict) or not metrics:
            return None

        total = int(metrics.get("total", 0) or 0)
        by_gate = metrics.get("by_gate", {}) or {}
        by_category = metrics.get("by_category", {}) or {}

        hotspot_gate = None
        if isinstance(by_gate, dict) and by_gate:
            hotspot_gate = max(by_gate.items(), key=lambda kv: kv[1])[0]

        dominant_category = None
        if isinstance(by_category, dict) and by_category:
            dominant_category = max(by_category.items(), key=lambda kv: kv[1])[0]

        return {
            "total": total,
            "by_gate": by_gate,
            "by_category": by_category,
            "hotspot_gate": hotspot_gate,
            "dominant_category": dominant_category,
        }

    def write_meta(self, meta: RunMeta) -> Path:
        data = asdict(meta)

        # normalize enums
        data["current_gate"] = str(meta.current_gate.value)
        data["status"] = str(meta.status.value)

        data["transitions"] = [
            {
                "from_gate": t.from_gate,
                "to_gate": t.to_gate,
                "decision": str(t.decision.value),
                "at": t.at,
            }
            for t in meta.transitions
        ]

        safe_summary = self._build_safe_mode_summary(meta)
        if safe_summary is not None:
            data["safe_mode_summary"] = safe_summary

        return self.write_json("META.json", data)
