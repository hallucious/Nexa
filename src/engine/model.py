from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .types import FlowPolicy


@dataclass(frozen=True)
class Channel:
    """Directional data path: src.output -> dst.input.

    v1: This is purely structural. Execution semantics are handled by Flow/Execution.
    """
    channel_id: str
    src_node_id: str
    dst_node_id: str
    # Optional port/field mapping (reserved for later, but structurally explicit)
    mapping: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class FlowRule:
    """Node-level flow (propagation) policy.

    v1: FlowRule is applied per *destination node* (node_id).
    If no FlowRule is provided for a node, the default policy is ALL_SUCCESS.

    rule_id is kept for traceability and future governance.
    payload remains as an explicit extension slot (no hidden logic).
    """
    rule_id: str
    node_id: str
    policy: FlowPolicy = FlowPolicy.ALL_SUCCESS
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineStructure:

    """Immutable structural snapshot for revisioning."""
    entry_node_id: str
    node_ids: List[str]
    channels: List[Channel] = field(default_factory=list)
    flow: List[FlowRule] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
