from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence

from .types import NodeStatus, StageStatus


@dataclass(frozen=True)
class NodeTrace:
    """Per-node execution evidence (immutable)."""

    node_id: str

    node_status: NodeStatus = NodeStatus.NOT_REACHED

    pre_status: StageStatus = StageStatus.SKIPPED
    core_status: StageStatus = StageStatus.SKIPPED
    post_status: StageStatus = StageStatus.SKIPPED

    reason_code: Optional[str] = None
    message: Optional[str] = None

    input_snapshot: Optional[Dict[str, Any]] = None
    output_snapshot: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ExecutionTrace:
    """Graph-based trace for a single Engine execution (immutable).

    Hard Requirement (docs/specs/trace_model.md v1.0.1):
    - Trace MUST include every node_id in the Engine graph.
    - Missing coverage invalidates the trace.
    """

    execution_id: str
    revision_id: str
    structural_fingerprint: str

    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    validation_success: Optional[bool] = None
    validation_violations: Optional[list] = None  # list[tuple[rule_id, message]] minimal

    nodes: Mapping[str, NodeTrace] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    # Required coverage source-of-truth
    expected_node_ids: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        missing = [nid for nid in self.expected_node_ids if nid not in self.nodes]
        if missing:
            raise ValueError(f"Trace missing node coverage: {missing}")
