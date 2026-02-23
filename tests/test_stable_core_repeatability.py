
import pytest
from pathlib import Path

from src.pipeline.runner import PipelineRunner
from src.pipeline.state import RunMeta, RunStatus
from src.utils.time import now_seoul


def test_stable_core_repeatability(tmp_path: Path):
    """Stable Core invariant: repeated identical runs must remain structurally consistent."""

    results = []

    for i in range(50):
        meta = RunMeta(run_id=f"REPEAT_{i}", created_at=now_seoul().isoformat())
        runner = PipelineRunner(meta=meta, run_dir=str(tmp_path / f"run_{i}"))

        runner.run()

        # Basic structural invariants
        assert meta.status in (RunStatus.PASS, RunStatus.STOP)
        assert meta.current_gate is not None

        # stop_reason must be enum string or None
        if meta.stop_reason is not None:
            assert isinstance(meta.stop_reason, str)
            assert meta.stop_reason.strip() != ""

        results.append((meta.status, meta.stop_reason))

    # All runs must produce identical final status/stop_reason
    first = results[0]
    for r in results[1:]:
        assert r == first
