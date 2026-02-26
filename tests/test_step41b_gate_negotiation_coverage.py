from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.runner import GateContext, RunMeta

from src.platform.g1_design_plugin import resolve as resolve_g1
from src.platform.g2_continuity_plugin import resolve as resolve_g2
from src.platform.g4_self_check_plugin import resolve as resolve_g4
from src.platform.g5_implement_test_plugin import resolve as resolve_g5
from src.platform.g7_final_review_plugin import resolve as resolve_g7


def _read_obs(run_dir: Path) -> list[dict]:
    p = run_dir / "OBSERVABILITY.jsonl"
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        out.append(json.loads(line))
    return out


def test_step41b_all_core_gates_negotiate(tmp_path: Path):
    """Ensure all core gates use centralized negotiation (single selection source of truth).

    This test is intentionally lightweight: calling each resolve(...) should emit
    CAPABILITY_NEGOTIATED into OBSERVABILITY.jsonl.
    """

    run_dir = tmp_path / "run"
    meta = RunMeta(run_id="r", created_at="2099-01-01T00:00:00Z")
    ctx = GateContext(meta=meta, run_dir=str(run_dir), context={}, providers={}, plugins={})

    # Resolve each gate plugin once.
    resolve_g1(ctx)
    resolve_g2(ctx)
    resolve_g4(ctx)
    resolve_g5(ctx)
    resolve_g7(ctx)

    events = [e for e in _read_obs(run_dir) if e.get("event") == "CAPABILITY_NEGOTIATED"]
    gate_ids = [e.get("gate_id") for e in events]

    # We expect at least one negotiation event per gate.
    for gid in ("G1", "G2", "G4", "G5", "G7"):
        assert gid in gate_ids
