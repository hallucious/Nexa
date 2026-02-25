from __future__ import annotations

from typing import Optional, Protocol, Any, Dict

from src.pipeline.runner import GateContext


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


def resolve_g5_exec_plugin(ctx: GateContext) -> Optional[G5ExecPlugin]:
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

def resolve(ctx: GateContext) -> Optional[G5ExecPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional exec plugin."""
    return resolve_g5_exec_plugin(ctx)
