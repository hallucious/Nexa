from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass(frozen=True)
class NodeModel:
    id: str
    raw: Dict[str, Any]
    kind: str = "unknown"
    label: Optional[str] = None
    execution: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EdgeModel:
    from_id: str
    to_id: str
    kind: str
    raw: Dict[str, Any]


@dataclass(frozen=True)
class CircuitModel:
    circuit_id: str
    nodes: Dict[str, NodeModel]
    edges: List[EdgeModel]
    entry_node_id: str
    raw: Dict[str, Any] = field(default_factory=dict)
    subcircuits: Dict[str, Dict[str, Any]] = field(default_factory=dict)
