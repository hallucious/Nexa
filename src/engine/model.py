from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    """Control rule placeholder.

    v1 skeleton: Flow is present as a structural component.
    Detailed control semantics are defined in future Flow spec iterations.
    """
    rule_id: str
    # Free-form rule payload (kept explicit, no hidden logic)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineStructure:
    """Immutable structural snapshot for revisioning."""
    entry_node_id: str
    node_ids: List[str]
    channels: List[Channel] = field(default_factory=list)
    flow: List[FlowRule] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
