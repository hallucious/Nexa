from __future__ import annotations

from typing import Any, Dict, Optional

from src.platform.fact_check_plugin import FactCheckPlugin, resolve_fact_check_plugin as _resolve_fact_check_plugin


def resolve_fact_check_plugin(*, plugins: Optional[Dict[str, Any]], provider: Any) -> FactCheckPlugin:
    """Gate G3 entrypoint for fact-check plugin resolution.

    This mirrors the legacy resolver signature used by Gate G3, but is placed in a
    per-gate module to keep plugin entrypoints consistent across gates.
    """
    return _resolve_fact_check_plugin(plugins=plugins, provider=provider)
