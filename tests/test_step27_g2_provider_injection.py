from pathlib import Path

from src.pipeline.state import RunMeta
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.gates.g2_continuity import gate_g2_continuity


class StubGPT:
    def generate_text(self, *, prompt: str, temperature: float, max_output_tokens: int):
        # Return valid JSON as text to satisfy Gate2 parsing
        return ('{"verdict":"SAME","rationale":"ok"}', {}, None)


def test_g2_uses_injected_gpt_provider_when_not_pytest(tmp_path, monkeypatch):
    # simulate non-pytest execution
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9200"
    baseline_dir = repo / "baseline"
    run_dir.mkdir(parents=True)
    baseline_dir.mkdir(parents=True)

    # PIC (baseline) + current text inputs
    (baseline_dir / "PIC.md").write_text("PIC baseline\n", encoding="utf-8")
    (run_dir / "G1_DECISION.md").write_text("CURRENT design\n", encoding="utf-8")

    # Minimal JSON artifacts for structure diff path
    (baseline_dir / "BASELINE_G1_OUTPUT.json").write_text('{"design": {"summary": "a"}}', encoding="utf-8")
    (run_dir / "G1_OUTPUT.json").write_text('{"design": {"summary": "a"}}', encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_9200", created_at=now_seoul().isoformat())
    ctx = GateContext(
        meta=meta,
        run_dir=str(run_dir),
        providers={"gpt": StubGPT()},
        context={},
    )

    res = gate_g2_continuity(ctx)
    assert res.decision.value in ("PASS", "FAIL", "STOP")

    out = (run_dir / "G2_OUTPUT.json").read_text(encoding="utf-8")
    assert '"gpt_used": true' in out
    assert '"verdict": "SAME"' in out
    assert '"rationale": "ok"' in out
