from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

from src.pipeline.runner import GateContext
from src.platform.capability_negotiation import negotiate
from src.platform.plugin_contract import ReasonCode, infer_reason_code, normalize_meta

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "g6_counterfactual",
    "type": "gate_plugin",
    "entrypoint": "src.platform.g6_counterfactual_plugin:resolve",
    "inject": {"target": "providers", "key": "g6_counterfactual"},
    "capabilities": ["counterfactual_generation"],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}



class CounterfactualPlugin(Protocol):
    """Pluggable execution surface for G6 counterfactual generation.

    Goal: keep gate logic stable while allowing controlled substitution of the
    text generation backend (e.g., gemini/gpt stub in tests).
    """

    def generate(
        self,
        ctx: GateContext,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_output_tokens: int = 1200,
    ) -> Tuple[str, Dict[str, Any], Optional[str], str]:
        """Return (text, meta, error, engine)."""


@dataclass(frozen=True)
class ProviderCounterfactualPlugin:
    """Default plugin: choose provider from ctx.providers (gemini preferred)."""

    def generate(
        self,
        ctx: GateContext,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_output_tokens: int = 1200,
    ) -> Tuple[str, Dict[str, Any], Optional[str], str]:
        # Step41: centralize selection; keep same priority: gemini > gpt
        sel = negotiate(
            gate_id="G6",
            capability="counterfactual_generation",
            ctx=ctx,
            priority_chain=[("providers", "gemini"), ("providers", "gpt")],
            required=False,
        )

        provider = sel.selected
        engine = sel.selected_key or "none"

        if provider is None:
            meta = normalize_meta(
                {},
                reason_code=ReasonCode.PROVIDER_MISSING,
                provider=engine,
                source="g6_counterfactual",
                error="provider_missing",
            )
            return "", meta, "provider missing: expected ctx.providers['gemini'|'gpt']", engine

        try:
            text, meta, err = provider.generate_text(
                prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            m = meta if isinstance(meta, dict) else {}
            rc = infer_reason_code(meta=m, error=err)
            m = normalize_meta(m, reason_code=rc, provider=engine, source="g6_counterfactual", error=err)
            return text or "", m, err, engine
        except Exception as e:
            err = f"provider error: {type(e).__name__}: {e}"
            meta = normalize_meta(
                {},
                reason_code=ReasonCode.PROVIDER_ERROR,
                provider=engine,
                source="g6_counterfactual",
                error=err,
            )
            return "", meta, err, engine


def resolve_g6_counterfactual_plugin(ctx: GateContext) -> CounterfactualPlugin:
    """Resolve the plugin to use for G6.

    - If ctx.providers contains a dedicated key, prefer it:
        ctx.providers["g6_counterfactual"]
    - Else fall back to ProviderCounterfactualPlugin.
    """
    sel = negotiate(
        gate_id="G6",
        capability="counterfactual_generation",
        ctx=ctx,
        priority_chain=[("providers", "g6_counterfactual")],
        required=False,
    )
    if sel.selected is not None:
        return sel.selected  # type: ignore[return-value]
    return ProviderCounterfactualPlugin()


def resolve(ctx: GateContext) -> Optional[CounterfactualPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional counterfactual plugin."""
    return resolve_g6_counterfactual_plugin(ctx)
