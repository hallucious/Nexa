
from __future__ import annotations

from src.platform.context import GateContextLike
from typing import Optional, Protocol, Any, Dict

from src.platform.capability_negotiation import negotiate

PLUGIN_MANIFEST = {
    "manifest_version": "1.0",
    "id": "g5_implement_test",
    "type": "tool",
    "entrypoint": "src.platform.g5_implement_test_plugin:resolve",
    "inject": {"target": "plugins", "key": "exec"},
    "capabilities": [],
    "requires": {"python": ">=3.8", "platform_api": ">=0.1,<2.0"},
    "determinism": {"required": True},
    "safety": {"timeout_ms": 120000}
}



class G5ExecPlugin(Protocol):
    """Gate G5 plugin interface (execution)."""

    def execute(
        self,
        cmd: list[str],
        *,
        cwd: str,
        env: Dict[str, str],
        timeout_s: int,
    ) -> Any:
        ...


def resolve_g5_exec_plugin(ctx: GateContextLike) -> Optional[G5ExecPlugin]:
    """Resolve the execution plugin for G5.

    Convention:
    - ctx.plugins["exec"] may hold a plugin implementing .execute(...)
    - If absent, the gate should fall back to subprocess.run (legacy behavior).
    """
    plugins = getattr(ctx, "plugins", None)
    if not isinstance(plugins, dict):
        return None

    p = plugins.get("exec")
    if p is None:
        return None

    if hasattr(p, "execute"):
        return p  # type: ignore[return-value]

    return None

def resolve(ctx: GateContextLike) -> Optional[G5ExecPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional exec plugin."""
    sel = negotiate(
        gate_id="G5",
        capability="exec_tool",
        ctx=ctx,
        priority_chain=[("plugins", "exec")],
        required=False,
    )
    p = sel.selected
    if p is None:
        return None
    if hasattr(p, "execute"):
        return p  # type: ignore[return-value]
    return None
