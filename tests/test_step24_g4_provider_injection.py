from pathlib import Path

from src.pipeline.state import RunMeta
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.gates.g4_self_check import gate_g4_self_check


class StubGPT:
    def __init__(self):
        self.called = False

    def generate_text(self, prompt: str, temperature: float = 0.0, max_output_tokens: int = 0):
        self.called = True
        return ("ok", {"stub": True}, None)


def test_g4_uses_injected_gpt_provider(tmp_path, monkeypatch):
    # simulate non-pytest execution
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9100"
    run_dir.mkdir(parents=True)

    # Minimal upstream artifacts to satisfy prereq checks
    (run_dir / "G1_OUTPUT.json").write_text(
        '{"design": {"requirements": ["a"], "interfaces": ["i"], "constraints": ["c"], "acceptance_criteria": ["ac"]}}',
        encoding="utf-8",
    )
    (run_dir / "G2_OUTPUT.json").write_text('{"baseline_present": true}', encoding="utf-8")
    (run_dir / "G3_OUTPUT.json").write_text('{"results": []}', encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_9100", created_at=now_seoul().isoformat())
    stub = StubGPT()

    ctx = GateContext(
        meta=meta,
        run_dir=str(run_dir),
        providers={"gpt": stub},
        context={},
    )

    res = gate_g4_self_check(ctx)
    assert res.decision.value in ("PASS", "FAIL", "STOP")

    # Ensure GPT injection path executed
    out = (run_dir / "G4_OUTPUT.json").read_text(encoding="utf-8")
    assert '"used": true' in out
    assert '"text": "ok"' in out
