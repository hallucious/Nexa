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
    def from_run_dir(run_dir: Path) -> "Artifacts":
        """Create an Artifacts helper from an existing run directory.

        Expected layout: <repo_root>/runs/<run_id>
        """
        run_dir = run_dir.resolve()
        run_id = run_dir.name
        repo_root = run_dir.parent.parent
        return Artifacts(repo_root=repo_root, run_id=run_id)

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

    def read_json(self, artifact_filename: str) -> Optional[dict]:
        p = self.path(artifact_filename)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def append_jsonl(self, artifact_filename: str, record: dict) -> Path:
        p = self.path(artifact_filename)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return p

    def update_json(self, artifact_filename: str, patch: dict) -> Path:
        """Read JSON (if present), deep-merge patch, write back."""
        data = self.read_json(artifact_filename) or {}
        merged = self._deep_merge_dict(data, patch)
        return self.write_json(artifact_filename, merged)

    @staticmethod
    def _deep_merge_dict(dst: dict, patch: dict) -> dict:
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                dst[k] = Artifacts._deep_merge_dict(dst[k], v)
            else:
                dst[k] = v
        return dst

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

        return self.write_json("META.json", data)
