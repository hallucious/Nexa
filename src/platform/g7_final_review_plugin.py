from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

from src.pipeline.runner import GateContext


class G7FinalReviewPlugin(Protocol):
    """Execution plugin for G7 final review."""

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Return (text, meta). Must not raise for normal operation."""


@dataclass
class _GPTAdapter:
    provider: Any

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        # Support either generate_text(prompt) or generate(prompt)
        if hasattr(self.provider, "generate_text"):
            resp = self.provider.generate_text(prompt)  # type: ignore[attr-defined]
        elif hasattr(self.provider, "generate"):
            resp = self.provider.generate(prompt)  # type: ignore[attr-defined]
        else:
            return ("", {"error": "provider_missing_generate_method"})

        # Normalize to (text, meta)
        if isinstance(resp, str):
            return (resp, {})

        if isinstance(resp, dict):
            text = str(resp.get("text") or resp.get("content") or resp.get("output") or "")
            meta = {k: v for k, v in resp.items() if k not in ("text", "content", "output")}
            return (text, meta)

        if isinstance(resp, (list, tuple)):
            text = str(resp[0]) if len(resp) >= 1 else ""
            meta: Dict[str, Any] = {"raw_type": type(resp).__name__, "raw_len": len(resp)}
            return (text, meta)

        return (str(resp), {"raw_type": type(resp).__name__})


def resolve_g7_final_review_plugin(ctx: GateContext) -> Optional[G7FinalReviewPlugin]:
    """Resolve plugin in a stable order.

    Priority:
    1) providers['g7_final_review'] (explicit plugin)
    2) providers['gpt'] (adapter)
    """

    providers = ctx.providers or {}

    plugin = providers.get("g7_final_review")
    if plugin is not None and hasattr(plugin, "generate"):
        return plugin  # type: ignore[return-value]

    gpt = providers.get("gpt")
    if gpt is not None:
        return _GPTAdapter(gpt)

    return None

def resolve(ctx: GateContext) -> Optional[G7FinalReviewPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional final review plugin."""
    return resolve_g7_final_review_plugin(ctx)
