
from __future__ import annotations

from src.platform.context import GateContextLike
from typing import Any, Dict, Optional

from src.platform.fact_check_plugin import FactCheckPlugin, resolve_fact_check_plugin as _resolve_fact_check_plugin, resolve_from_ctx

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "g3_fact_audit",
    "type": "gate_plugin",
    "entrypoint": "src.platform.g3_fact_audit_plugin:resolve",
    "inject": {"target": "providers", "key": "perplexity"},
    "capabilities": ["fact_check"],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}



def resolve_fact_check_plugin(*, plugins: Optional[Dict[str, Any]], provider: Any) -> FactCheckPlugin:
    """Gate G3 entrypoint for fact-check plugin resolution.

    This mirrors the legacy resolver signature used by Gate G3, but is placed in a
    per-gate module to keep plugin entrypoints consistent across gates.
    """
    return _resolve_fact_check_plugin(plugins=plugins, provider=provider)

def resolve(ctx: "GateContextLike") -> Optional[FactCheckPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional fact-check plugin."""
    return resolve_from_ctx(ctx)
