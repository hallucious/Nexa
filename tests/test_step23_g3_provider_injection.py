from pathlib import Path

from src.pipeline.state import RunMeta
from src.pipeline.runner import GateContext
from src.gates.g3_fact_audit import gate_g3_fact_audit
from src.utils.time import now_seoul


class StubPerplexity:
    def verify(self, stmt: str):
        # return the shape expected by gate_g3_fact_audit
        return {
            "verdict": "OK",
            "confidence": 1.0,
            "citations": [],
            "summary": "stubbed",
        }


def test_g3_uses_injected_provider_when_not_pytest(tmp_path, monkeypatch):
    # simulate non-pytest execution
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9002"
    run_dir.mkdir(parents=True)

    # minimal G1 output with a fact-like statement to trigger candidate extraction
    (run_dir / "G1_OUTPUT.json").write_text(
        '{"design": {"summary": "Ensure contracts must pass."}}',
        encoding="utf-8",
    )

    meta = RunMeta(run_id="2099-01-01_9002", created_at=now_seoul().isoformat())

    ctx = GateContext(
        meta=meta,
        run_dir=str(run_dir),
        providers={"perplexity": StubPerplexity()},
        context={},
    )

    result = gate_g3_fact_audit(ctx)
    # should not STOP due to missing PERPLEXITY_API_KEY because provider is injected
    assert result.decision.value in ("PASS", "FAIL")  # rule-based could still FAIL depending on rules
