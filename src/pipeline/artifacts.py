from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

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

    def write_meta(self, meta) -> Path:
        """Write META.json.

        Tolerant serializer: RunMeta may gain new fields over time.
        We serialize core fields plus optional observability fields when present.
        """
        meta_path = self.run_dir / "META.json"

        data = {
            "run_id": getattr(meta, "run_id", None),
            "created_at": getattr(meta, "created_at", None),
            "status": getattr(meta, "status", "RUNNING"),
            "transitions": getattr(meta, "transitions", []) or [],
        }

        # Optional fields for long-term observability (C: Gate metrics to META)
        for key in (
            "gate_metrics",
            "safe_mode_summary",
            "auto_tuning_hints",
            "warnings",
            "errors",
        ):
            if hasattr(meta, key):
                val = getattr(meta, key)
                if val is not None:
                    data[key] = val

        meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta_path