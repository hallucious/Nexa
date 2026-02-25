from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import pytest

from src.pipeline.runner import GateContext
from src.pipeline.state import RunMeta
from src.platform.plugin_contract import CONTRACT_VERSION, ReasonCode, REQUIRED_META_KEYS


@dataclass
class _TupleProvider:
    """Provider that mimics (text, meta, err) return shape."""

    text: str = "ok"
    meta: Dict[str, Any] = None  # type: ignore[assignment]
    err: Optional[str] = None

    def __post_init__(self) -> None:
        if self.meta is None:
            self.meta = {"provider_hint": "tuple"}

    def generate_text(self, *args: Any, **kwargs: Any) -> Tuple[str, Dict[str, Any], Optional[str]]:
        return (self.text, dict(self.meta), self.err)


@dataclass
class _DictProvider:
    """Provider that returns a dict payload (used by adapters that accept dict)."""

    def generate_text(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {"text": "ok", "provider_hint": "dict"}


def _mk_ctx() -> GateContext:
    meta = RunMeta(run_id="test", created_at="2099-01-01T00:00:00Z")
    return GateContext(
        meta=meta,
        run_dir=".",
        context={},
        providers={
            "gemini": _TupleProvider(),
            "gpt": _DictProvider(),
        },
        plugins={},
    )


def _assert_meta(meta: Dict[str, Any]) -> None:
    assert isinstance(meta, dict)
    for k in REQUIRED_META_KEYS:
        assert k in meta, f"missing required meta key: {k}"

    assert meta["contract_version"] == CONTRACT_VERSION
    assert meta["reason_code"] in {rc.value for rc in ReasonCode}
    assert isinstance(meta["provider"], str) and meta["provider"]
    assert isinstance(meta["source"], str) and meta["source"]


def test_step30_g7_meta_contract() -> None:
    from src.platform import g7_final_review_plugin

    ctx = _mk_ctx()
    plug = g7_final_review_plugin.resolve(ctx)
    assert plug is not None

    _text, meta = plug.generate("ping")
    _assert_meta(meta)


def test_step30_g6_meta_contract() -> None:
    from src.platform import g6_counterfactual_plugin

    ctx = _mk_ctx()
    plug = g6_counterfactual_plugin.resolve(ctx)
    assert plug is not None

    _text, meta, _err, _engine = plug.generate(ctx, "ping")
    _assert_meta(meta)


def test_step30_g4_meta_contract() -> None:
    from src.platform.g4_self_check_plugin import G4SelfCheckPlugin

    ctx = _mk_ctx()
    res = G4SelfCheckPlugin().run(ctx)
    _assert_meta(res.meta)
