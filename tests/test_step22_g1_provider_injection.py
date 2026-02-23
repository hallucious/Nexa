from pathlib import Path

from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.utils.time import now_seoul
from src.gates.g1_design import gate_g1_design


class StubGPT:
    def generate_json(self, system: str, user: str, schema: dict):
        # minimal valid design payload for G1 contract
        return {"design": {"summary": "stub", "files": []}}


def test_g1_uses_injected_provider_when_not_pytest(tmp_path: Path, monkeypatch):
    # simulate non-pytest execution (G1 should try to use injected provider)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9001"
    run_dir.mkdir(parents=True)
    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_9001", created_at=now_seoul().isoformat())
    stub = StubGPT()

    # GateContext now has a first-class 'providers' field (A7-4 plumbing).
    ctx = GateContext(meta=meta, run_dir=str(run_dir), context={}, providers={"gpt": stub})

    result = gate_g1_design(ctx)

    assert result.decision.value in ("PASS", "FAIL", "STOP")
    # If injected provider is used, G1 should not STOP for missing OPENAI_API_KEY.
    assert not (result.decision.value == "STOP" and "OPENAI_API_KEY" in (result.meta or {}).get("stop_reason", ""))
