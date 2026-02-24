
import json
from pathlib import Path

from src.gates.g6_counterfactual import gate_g6_counterfactual_review
from src.pipeline.runner import RunMeta
from src.gates.gate_common import GateContext
from src.utils.time import now_seoul


def test_g6_output_schema_snapshot(tmp_path):
    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "2099-01-01_9999"
    run_dir.mkdir(parents=True)

    # minimal prereqs
    (run_dir / "00_USER_REQUEST.md").write_text("Build pipeline\n", encoding="utf-8")
    (run_dir / "G1_OUTPUT.json").write_text('{"design": {"summary": "x"}}', encoding="utf-8")
    (run_dir / "G2_OUTPUT.json").write_text('{"baseline_present": true}', encoding="utf-8")
    (run_dir / "G3_OUTPUT.json").write_text('{"results": []}', encoding="utf-8")
    (run_dir / "G4_OUTPUT.json").write_text('{"checks": []}', encoding="utf-8")
    (run_dir / "G5_OUTPUT.json").write_text('{"result": {"returncode": 0}}', encoding="utf-8")

    for gid in ["G1","G2","G3","G4","G5"]:
        (run_dir / f"{gid}_DECISION.md").write_text(f"# {gid}\n\nDecision: PASS\n", encoding="utf-8")

    meta = RunMeta(run_id="2099-01-01_9999", created_at=now_seoul().isoformat())
    ctx = GateContext(meta=meta, run_dir=str(run_dir), providers={}, context={})

    gate_g6_counterfactual_review(ctx)

    output_path = run_dir / "G6_OUTPUT.json"
    assert output_path.exists()

    out = json.loads(output_path.read_text(encoding="utf-8"))

    # snapshot contract assertions
    assert set(out.keys()) >= {
        "gate",
        "status",
        "summary",
        "counterfactuals",
    }

    assert out["gate"] == "G6"
    assert isinstance(out["counterfactuals"], list)
