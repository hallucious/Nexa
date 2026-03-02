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


    # ---------------------------------------------------------------------
    # Serialization API (docs/specs/trace_model.md v1.2.0)
    # ---------------------------------------------------------------------

    @staticmethod
    def _ensure_json_safe(value: Any, *, path: str = "$") -> Any:
        """Validate that a value is JSON-safe and normalize where needed.

        Allowed types:
        - dict (str keys only), list/tuple, str, int, float, bool, None
        """
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (list, tuple)):
            return [ExecutionTrace._ensure_json_safe(v, path=f"{path}[{i}]") for i, v in enumerate(value)]
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for k, v in value.items():
                if not isinstance(k, str):
                    raise TypeError(f"Non-string dict key at {path}: {type(k).__name__}")
                out[k] = ExecutionTrace._ensure_json_safe(v, path=f"{path}.{k}")
            return out
        raise TypeError(f"Non-JSON-safe type at {path}: {type(value).__name__}")

    def to_dict(self, *, stable: bool = True) -> Dict[str, Any]:
        """Serialize this trace into a JSON-safe dict.

        Determinism contract:
        - stable=True => nodes are emitted in sorted(node_id) order
        - enums -> .value, datetime -> isoformat()
        - meta/input/output snapshots must be JSON-safe; otherwise TypeError
        """

        def _dt(d: Optional[datetime]) -> Optional[str]:
            return d.isoformat() if d is not None else None

        def _node_dict(nt: NodeTrace, *, node_path: str) -> Dict[str, Any]:
            return {
                "node_id": nt.node_id,
                "node_status": nt.node_status.value,
                "pre_status": nt.pre_status.value,
                "core_status": nt.core_status.value,
                "post_status": nt.post_status.value,
                "reason_code": nt.reason_code,
                "message": nt.message,
                "input_snapshot": ExecutionTrace._ensure_json_safe(nt.input_snapshot, path=f"{node_path}.input_snapshot")
                if nt.input_snapshot is not None
                else None,
                "output_snapshot": ExecutionTrace._ensure_json_safe(nt.output_snapshot, path=f"{node_path}.output_snapshot")
                if nt.output_snapshot is not None
                else None,
                "meta": ExecutionTrace._ensure_json_safe(nt.meta, path=f"{node_path}.meta") if nt.meta is not None else None,
            }

        node_ids = sorted(self.nodes.keys()) if stable else list(self.nodes.keys())
        nodes_out: Dict[str, Any] = {}
        for nid in node_ids:
            nodes_out[nid] = _node_dict(self.nodes[nid], node_path=f"$.nodes['{nid}']")

        meta_out = ExecutionTrace._ensure_json_safe(self.meta, path="$.meta") if self.meta is not None else {}

        return {
            "execution_id": self.execution_id,
            "revision_id": self.revision_id,
            "structural_fingerprint": self.structural_fingerprint,
            "started_at": _dt(self.started_at),
            "finished_at": _dt(self.finished_at),
            "duration_ms": self.duration_ms,
            "validation_success": self.validation_success,
            "validation_violations": ExecutionTrace._ensure_json_safe(self.validation_violations, path="$.validation_violations")
            if self.validation_violations is not None
            else None,
            "expected_node_ids": list(self.expected_node_ids),
            "nodes": nodes_out,
            "meta": meta_out,
        }

    def to_json(
        self,
        *,
        stable: bool = True,
        ensure_ascii: bool = False,
        indent: Optional[int] = None,
    ) -> str:
        """Serialize to deterministic JSON string when stable=True."""
        import json

        return json.dumps(
            self.to_dict(stable=stable),
            sort_keys=bool(stable),
            ensure_ascii=ensure_ascii,
            indent=indent,
        )

