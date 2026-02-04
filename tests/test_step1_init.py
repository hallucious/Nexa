from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.artifacts import Artifacts
from src.pipeline.state import RunMeta
from src.utils.time import make_run_id, now_seoul


def test_make_run_id_format():
    rid = make_run_id(now_seoul())
    assert len(rid) == 15  # YYYY-MM-DD_HHMM
    assert rid[4] == "-" and rid[7] == "-" and rid[10] == "_"


def test_artifacts_create_and_meta(tmp_path: Path):
    repo_root = tmp_path
    (repo_root / "runs").mkdir(parents=True)

    rid = "2099-12-31_2359"
    a = Artifacts.create_new(repo_root=repo_root, run_id=rid)

    assert a.run_dir.exists()
    meta = RunMeta(run_id=rid, created_at="2099-12-31T23:59:00+09:00")
    a.write_meta(meta)

    meta_path = a.run_dir / "META.json"
    assert meta_path.exists()

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["run_id"] == rid
    assert data["status"] == "RUNNING"
