from pathlib import Path

from src.gates.g6_counterfactual import gate_g6_counterfactual_review
from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.utils.time import now_seoul


class StubGemini:
    def generate_text(self, prompt, temperature=0.0, max_output_tokens=1000):
        return "ok", {}, None


def test_g6_uses_injected_gemini_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9400"
    run_dir.mkdir(parents=True)

    # minimal prereqs expected by G6
    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")
    (run_dir / "G1_OUTPUT.json").write_text('{"design": {"summary": "x"}}', encoding="utf-8")
    (run_dir / "G2_OUTPUT.json").write_text('{"baseline_present": true}', encoding="utf-8")
    (run_dir / "G3_OUTPUT.json").write_text('{"results": []}', encoding="utf-8")
    (run_dir / "G4_OUTPUT.json").write_text('{"checks": []}', encoding="utf-8")
    (run_dir / "G5_OUTPUT.json").write_text('{"result": {"returncode": 0}}', encoding="utf-8")

    for gid in ["G1","G2","G3","G4","G5"]:
        (run_dir / f"{gid}_DECISION.md").write_text(f"# {gid}\n\nDecision: PASS\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_9400", created_at=now_seoul().isoformat())
    ctx = GateContext(meta=meta, run_dir=str(run_dir), providers={"gemini": StubGemini()}, context={})

    res = gate_g6_counterfactual_review(ctx)
    assert res.decision.value in ("PASS", "FAIL", "STOP")

    out = (run_dir / "G6_OUTPUT.json").read_text(encoding="utf-8")

    # We only assert the injection path is taken and no "provider missing" error is recorded.
    assert '"engine": "gemini"' in out
    assert '"used": true' in out
    assert "provider missing" not in out.lower()
