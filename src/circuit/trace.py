
from dataclasses import dataclass, field
from typing import Any, List, Optional
from datetime import datetime
import uuid

def _now():
    return datetime.utcnow().isoformat()

@dataclass
class ConditionResult:
    expression: Optional[str]
    value: Optional[bool]
    error: Optional[str]

@dataclass
class SelectedEdge:
    from_node_id: str
    to_node_id: str
    edge_id: Optional[str]
    priority: Optional[int]

@dataclass
class SnapshotRef:
    kind: str
    data: Optional[dict]
    note: Optional[str]

@dataclass
class NodeTrace:
    node_id: str
    entered_at: str
    exited_at: Optional[str] = None
    status: Optional[str] = None
    selected_edge: Optional[SelectedEdge] = None
    condition_result: Optional[ConditionResult] = None
    input_snapshot: Optional[SnapshotRef] = None
    output_snapshot: Optional[SnapshotRef] = None

@dataclass
class CircuitTrace:
    circuit_id: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=_now)
    finished_at: Optional[str] = None
    final_status: Optional[str] = None
    nodes: List[NodeTrace] = field(default_factory=list)
