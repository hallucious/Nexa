
from __future__ import annotations

from src.platform.context import GateContextLike
"""Capability Negotiation v1.

Goal: centralize deterministic selection of plugins/providers by capability.

This module does NOT load external plugins. It only selects from already-injected
objects in GateContextLike:
  - ctx.providers
  - ctx.plugins
  - ctx.context["plugins"]

Step41 introduces a single source of truth for:
  - priority chains
  - missing vs required-missing policy
  - observability trace events
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.platform.observability import append_observability_event
from src.platform.plugin_contract import ReasonCode


InjectTarget = str  # "providers" | "plugins" | "context.plugins"
PriorityItem = Tuple[InjectTarget, str]


@dataclass(frozen=True)
class NegotiationResult:
    gate_id: str
    capability: str
    required: bool
    selected_target: Optional[InjectTarget]
    selected_key: Optional[str]
    selected: Any
    missing: bool
    reason_code: ReasonCode
    priority_chain: List[PriorityItem]


def _get_context_plugins(ctx: GateContextLike) -> Dict[str, Any]:
    try:
        plugs = (ctx.context or {}).get("plugins")
        return plugs if isinstance(plugs, dict) else {}
    except Exception:
        return {}


def _lookup(ctx: GateContextLike, target: InjectTarget, key: str) -> Any:
    if target == "providers":
        return (ctx.providers or {}).get(key)
    if target == "plugins":
        return (ctx.plugins or {}).get(key)
    if target == "context.plugins":
        return _get_context_plugins(ctx).get(key)
    return None


def negotiate(
    *,
    gate_id: str,
    capability: str,
    ctx: GateContextLike,
    priority_chain: Sequence[PriorityItem],
    required: bool = False,
    emit_observability: bool = True,
) -> NegotiationResult:
    """Select an injected object by deterministic priority chain.

    - If found: returns selected object + CAPABILITY_SELECTED.
    - If missing:
        - optional => CAPABILITY_MISSING
        - required => CAPABILITY_REQUIRED_MISSING

    Always deterministic: first match wins.
    """

    chain = list(priority_chain)
    selected_target: Optional[InjectTarget] = None
    selected_key: Optional[str] = None
    selected_obj: Any = None

    for tgt, k in chain:
        obj = _lookup(ctx, tgt, k)
        if obj is not None:
            selected_target, selected_key, selected_obj = tgt, k, obj
            break

    missing = selected_obj is None
    if missing:
        rc = ReasonCode.CAPABILITY_REQUIRED_MISSING if required else ReasonCode.CAPABILITY_MISSING
    else:
        rc = ReasonCode.CAPABILITY_SELECTED

    res = NegotiationResult(
        gate_id=gate_id,
        capability=capability,
        required=required,
        selected_target=selected_target,
        selected_key=selected_key,
        selected=selected_obj,
        missing=missing,
        reason_code=rc,
        priority_chain=chain,
    )

    if emit_observability:
        try:
            append_observability_event(
                run_dir=ctx.run_dir,
                event={
                    "event": "CAPABILITY_NEGOTIATED",
                    "gate_id": gate_id,
                    "capability": capability,
                    "required": required,
                    "selected": None
                    if missing
                    else {"target": selected_target, "key": selected_key},
                    "missing": missing,
                    "priority_chain": [{"target": t, "key": k} for (t, k) in chain],
                    "reason_code": rc.value,
                },
            )
        except Exception:
            pass

    return res
