from __future__ import annotations

from pathlib import Path

from src.pipeline.cli import build_default_runner
from src.pipeline.state import RunMeta, RunStatus
from src.utils.time import now_seoul


def test_cli_build_default_runner_registers_7_gates(tmp_path: Path):
    meta = RunMeta(run_id="TEST_CLI", created_at=now_seoul().isoformat())
    runner = build_default_runner(run_dir=str(tmp_path), meta=meta)

    snap = runner.registered_gates()
    assert set(snap.keys()) == {"G1", "G2", "G3", "G4", "G5", "G6", "G7"}

    # smoke run: ensure it can execute when request file exists in run_dir
    # We don't need real request parsing here; gates may read run_dir artifacts.
    # The contract-pass gates in other tests cover success paths; here we just
    # ensure runner creation doesn't alter status.
    assert meta.status == RunStatus.RUNNING
