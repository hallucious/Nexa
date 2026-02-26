from __future__ import annotations

from pathlib import Path

from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.platform.capability_negotiation import negotiate
from src.platform.plugin_contract import ReasonCode


def _mk_ctx(tmp_path: Path, *, providers=None, plugins=None, context=None) -> GateContext:
    meta = RunMeta(run_id="r", created_at="2099-01-01T00:00:00")
    return GateContext(
        meta=meta,
        run_dir=str(tmp_path / "run"),
        context=dict(context or {}),
        providers=dict(providers or {}),
        plugins=dict(plugins or {}),
    )


def test_step41_optional_missing_returns_capability_missing(tmp_path: Path) -> None:
    ctx = _mk_ctx(tmp_path)
    res = negotiate(
        gate_id="G6",
        capability="counterfactual_generation",
        ctx=ctx,
        priority_chain=[("providers", "g6_counterfactual"), ("providers", "gemini")],
        required=False,
    )
    assert res.missing is True
    assert res.selected is None
    assert res.reason_code == ReasonCode.CAPABILITY_MISSING


def test_step41_required_missing_returns_required_missing(tmp_path: Path) -> None:
    ctx = _mk_ctx(tmp_path)
    res = negotiate(
        gate_id="G6",
        capability="counterfactual_generation",
        ctx=ctx,
        priority_chain=[("providers", "g6_counterfactual")],
        required=True,
    )
    assert res.missing is True
    assert res.reason_code == ReasonCode.CAPABILITY_REQUIRED_MISSING


def test_step41_first_match_wins_and_is_deterministic(tmp_path: Path) -> None:
    ctx = _mk_ctx(tmp_path, providers={"gpt": object(), "gemini": object()})
    res = negotiate(
        gate_id="G6",
        capability="counterfactual_generation",
        ctx=ctx,
        priority_chain=[("providers", "gemini"), ("providers", "gpt")],
        required=False,
    )
    assert res.missing is False
    assert res.selected_key == "gemini"
    assert res.reason_code == ReasonCode.CAPABILITY_SELECTED


def test_step41_context_override_beats_provider(tmp_path: Path) -> None:
    override = object()
    ctx = _mk_ctx(
        tmp_path,
        context={"plugins": {"fact_check": override}},
        providers={"perplexity": object()},
    )
    res = negotiate(
        gate_id="G3",
        capability="fact_check",
        ctx=ctx,
        priority_chain=[("context.plugins", "fact_check"), ("providers", "perplexity")],
        required=False,
    )
    assert res.missing is False
    assert res.selected is override
    assert res.selected_target == "context.plugins"
