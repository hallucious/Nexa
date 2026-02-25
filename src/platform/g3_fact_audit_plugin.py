from __future__ import annotations

from typing import Any, Dict, Optional

from src.pipeline.runner import GateContext
from src.platform.fact_check_plugin import FactCheckPlugin, resolve_fact_check_plugin as _resolve_fact_check_plugin


def resolve_fact_check_plugin(*, plugins: Optional[Dict[str, Any]], provider: Any) -> FactCheckPlugin:
    """Gate G3 entrypoint for fact-check plugin resolution.

    This mirrors the legacy resolver signature used by Gate G3, but is placed in a
    per-gate module to keep plugin entrypoints consistent across gates.
    """
    return _resolve_fact_check_plugin(plugins=plugins, provider=provider)

def resolve(ctx: "GateContext") -> Optional[FactCheckPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional fact-check plugin."""
    plugins = getattr(ctx, "plugins", None)
    providers = getattr(ctx, "providers", None) or {}
    provider = providers.get("perplexity")
    return _resolve_fact_check_plugin(plugins=plugins, provider=provider)
