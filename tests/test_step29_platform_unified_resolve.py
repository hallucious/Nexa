from __future__ import annotations

from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.platform import (
    g1_design_plugin,
    g2_continuity_plugin,
    g3_fact_audit_plugin,
    g4_self_check_plugin,
    g5_implement_test_plugin,
    g6_counterfactual_plugin,
    g7_final_review_plugin,
)

def _ctx() -> GateContext:
    meta = RunMeta(run_id="TEST", created_at="2099-01-01T00:00:00Z")
    return GateContext(meta=meta, run_dir=".", context={}, providers={}, plugins={})

def test_platform_plugins_expose_unified_resolve():
    ctx = _ctx()
    assert callable(g1_design_plugin.resolve)
    assert callable(g2_continuity_plugin.resolve)
    assert callable(g3_fact_audit_plugin.resolve)
    assert callable(g4_self_check_plugin.resolve)
    assert callable(g5_implement_test_plugin.resolve)
    assert callable(g6_counterfactual_plugin.resolve)
    assert callable(g7_final_review_plugin.resolve)

    # Smoke: should not raise
    _ = g1_design_plugin.resolve(ctx)
    _ = g2_continuity_plugin.resolve(ctx)
    _ = g3_fact_audit_plugin.resolve(ctx)
    _ = g4_self_check_plugin.resolve(ctx)
    _ = g5_implement_test_plugin.resolve(ctx)
    _ = g6_counterfactual_plugin.resolve(ctx)
    _ = g7_final_review_plugin.resolve(ctx)
