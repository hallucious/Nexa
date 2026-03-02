from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass(frozen=True)
class NodeModel:
    id: str
    raw: Dict[str, Any]


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
    raw: Dict[str, Any]
