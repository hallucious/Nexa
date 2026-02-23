
import json
from pathlib import Path
from src.pipeline.state import RunMeta
from src.pipeline.runner import GateContext
from src.utils.time import now_seoul
from src.gates.g2_continuity import gate_g2_continuity

class StubGPTUnknown:
    def __init__(self):
        self.model = "stub-model"
    def generate_text(self, *, prompt: str, temperature: float, max_output_tokens: int):
        return ('{"verdict":"UNKNOWN","rationale":"uncertain"}', {}, None)

def test_g2_unknown_with_provider_triggers_stop(tmp_path, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_STOP"
    baseline_dir = repo / "baseline"
    run_dir.mkdir(parents=True)
    baseline_dir.mkdir(parents=True)

    (baseline_dir / "BASELINE_G1_OUTPUT.json").write_text('{"a":1}', encoding="utf-8")
    (run_dir / "G1_OUTPUT.json").write_text('{"a":1}', encoding="utf-8")
    (run_dir / "G1_DECISION.md").write_text("CURRENT", encoding="utf-8")
    (baseline_dir / "PIC.md").write_text("PIC", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_STOP", created_at=now_seoul().isoformat())
    ctx = GateContext(meta=meta, run_dir=str(run_dir), providers={"gpt": StubGPTUnknown()}, context={})

    res = gate_g2_continuity(ctx)
    assert res.decision.value == "STOP"

    meta_json = json.loads((run_dir / "META.json").read_text(encoding="utf-8"))
    assert meta_json.get("stop_reason") == "G2_SEMANTIC_UNKNOWN_WITH_PROVIDER"