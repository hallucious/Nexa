from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

from src.pipeline.runner import GateContext


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
        provider = None
        engine = "none"

        # Preference order is part of the current contract:
        # - If a gemini provider is injected, use it (tests rely on this)
        # - Else use gpt if available
        if isinstance(getattr(ctx, "providers", None), dict):
            if "gemini" in ctx.providers:
                provider = ctx.providers["gemini"]
                engine = "gemini"
            elif "gpt" in ctx.providers:
                provider = ctx.providers["gpt"]
                engine = "gpt"

        if provider is None:
            return "", {}, "provider missing: expected ctx.providers['gemini'|'gpt']", engine

        try:
            text, meta, err = provider.generate_text(
                prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            # Some providers may return None meta; normalize to dict
            return text or "", meta or {}, err, engine
        except Exception as e:
            return "", {}, f"provider error: {type(e).__name__}: {e}", engine


def resolve_g6_counterfactual_plugin(ctx: GateContext) -> CounterfactualPlugin:
    """Resolve the plugin to use for G6.

    - If ctx.providers contains a dedicated key, prefer it:
        ctx.providers["g6_counterfactual"]
    - Else fall back to ProviderCounterfactualPlugin.
    """
    if isinstance(getattr(ctx, "providers", None), dict):
        plug = ctx.providers.get("g6_counterfactual")
        if plug is not None:
            return plug  # type: ignore[return-value]
    return ProviderCounterfactualPlugin()
