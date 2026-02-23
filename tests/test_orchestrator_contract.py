from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.decision_models import Decision
from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.utils.time import now_seoul

from src.platform.prompt_spec import PromptSpec
from src.platform.worker import WorkerResult
from src.platform.orchestrator import GateBlueprint, GateOrchestrator


class _FakeWorker:
    name = "fake"

    def __init__(self, *, succeed: bool = True) -> None:
        self._succeed = bool(succeed)

    def generate_text(self, *, prompt: str, temperature: float = 0.0, max_output_tokens: int = 1024, instructions: Optional[str] = None) -> WorkerResult:
        if self._succeed:
            return WorkerResult(
                success=True,
                text="ok",
                raw={"prompt": prompt},
                error=None,
                latency_ms=1,
                worker_name="fake",
            )
        return WorkerResult(
            success=False,
            text="",
            raw={"prompt": prompt},
            error="boom",
            latency_ms=1,
            worker_name="fake",
        )


def _ctx(tmp_path: Path) -> GateContext:
    meta = RunMeta(run_id="TEST_ORCH", created_at=now_seoul().isoformat())
    return GateContext(meta=meta, run_dir=str(tmp_path), context={"name": "Bob"}, providers={})


def test_orchestrator_builds_gate_and_writes_contract_artifacts(tmp_path: Path):
    spec = PromptSpec(id="g1_design/v1", version="v1", template="Hello {name}!", inputs_schema={"name": str})
    bp = GateBlueprint(gate_prefix="G1", prompt_spec=spec, worker=_FakeWorker(succeed=True))
    orch = GateOrchestrator()
    gate = orch.build(bp)

    result = gate(_ctx(tmp_path))

    assert result.decision == Decision.PASS
    assert (tmp_path / "G1_DECISION.md").exists()
    assert (tmp_path / "G1_OUTPUT.json").exists()
    assert (tmp_path / "G1_META.json").exists()


def test_orchestrator_worker_failure_becomes_stop(tmp_path: Path):
    spec = PromptSpec(id="g1_design/v1", version="v1", template="Hello {name}!", inputs_schema={"name": str})
    bp = GateBlueprint(gate_prefix="G1", prompt_spec=spec, worker=_FakeWorker(succeed=False))
    orch = GateOrchestrator()
    gate = orch.build(bp)

    result = gate(_ctx(tmp_path))

    assert result.decision == Decision.STOP
    assert (tmp_path / "G1_DECISION.md").exists()
