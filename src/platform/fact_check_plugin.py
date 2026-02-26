from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "fact_check",
    "type": "gate_plugin",
    "entrypoint": "src.platform.fact_check_plugin:resolve_fact_check_plugin",
    "inject": {"target": "context.plugins", "key": "fact_check"},
    "capabilities": [],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}



class FactCheckPlugin(Protocol):
    """Plugin contract for G3 fact verification.

    This abstracts *how* claims are verified (LLM, search API, offline DB, etc.).
    The gate should treat this as an optional capability.
    """

    def verify(self, claim: str) -> Dict[str, Any]:
        """Return a structured verification payload for a single claim."""


@dataclass(frozen=True)
class ProviderBackedFactCheckPlugin:
    """Adapter: wraps an existing provider that exposes a `verify` method."""

    provider: Any

    def verify(self, claim: str) -> Dict[str, Any]:
        # Defensive: provider contract is external to plugin.
        return self.provider.verify(claim)


def resolve_fact_check_plugin(
    plugins: Optional[Dict[str, Any]],
    provider: Any,
) -> Optional[FactCheckPlugin]:
    """Resolve the fact-check plugin from ctx.context plugins or fallback provider.

    Precedence:
      1) ctx.context["plugins"]["fact_check"] if present
      2) ProviderBackedFactCheckPlugin(provider) if provider has verify()
      3) None
    """

    if plugins and isinstance(plugins, dict):
        p = plugins.get("fact_check")
        if p is not None:
            return p  # trust caller

    if provider is not None and hasattr(provider, "verify"):
        return ProviderBackedFactCheckPlugin(provider=provider)

    return None
