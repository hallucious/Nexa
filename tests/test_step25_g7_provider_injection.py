from pathlib import Path

from src.gates.g7_final_review import gate_g7_final_review
from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.utils.time import now_seoul


class StubGPT:
    def generate_text(self, prompt, temperature=0.0, max_output_tokens=1000):
        return "ok", {"prompt_len": len(prompt)}, None


def test_g7_uses_injected_gpt_provider(tmp_path, monkeypatch):
    # simulate non-pytest execution
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9300"
    run_dir.mkdir(parents=True)

    # required outputs (minimal)
    (run_dir / "G1_OUTPUT.json").write_text('{"design": {"summary": "x"}}', encoding="utf-8")
    (run_dir / "G2_OUTPUT.json").write_text('{"baseline_present": true}', encoding="utf-8")
    (run_dir / "G3_OUTPUT.json").write_text('{"results": []}', encoding="utf-8")
    (run_dir / "G4_OUTPUT.json").write_text('{"checks": []}', encoding="utf-8")
    (run_dir / "G5_OUTPUT.json").write_text('{"result": {"returncode": 0}}', encoding="utf-8")
    (run_dir / "G6_OUTPUT.json").write_text('{"conflicts": []}', encoding="utf-8")

    # decisions
    for gid in ["G1","G2","G3","G4","G5","G6"]:
        (run_dir / f"{gid}_DECISION.md").write_text(f"# {gid}\n\nDecision: PASS\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_9300", created_at=now_seoul().isoformat())
    ctx = GateContext(meta=meta, run_dir=str(run_dir), providers={"gpt": StubGPT()}, context={})

    res = gate_g7_final_review(ctx)
    assert res.decision.value in ("PASS", "FAIL", "STOP")

    out = (run_dir / "G7_OUTPUT.json").read_text(encoding="utf-8")
    assert '"used": true' in out
    assert '"text": "ok"' in out
