from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .fingerprint import StructuralFingerprint, compute_fingerprint
from .model import Channel, EngineStructure, FlowRule
from .revision import Revision
from .trace import ExecutionTrace, NodeTrace
from .types import NodeStatus, StageStatus


@dataclass
class Engine:
    entry_node_id: str
    node_ids: List[str]
    channels: List[Channel] = field(default_factory=list)
    flow: List[FlowRule] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_structure(self) -> EngineStructure:
        return EngineStructure(
            entry_node_id=self.entry_node_id,
            node_ids=list(self.node_ids),
            channels=list(self.channels),
            flow=list(self.flow),
            meta=dict(self.meta),
        )

    def fingerprint(self) -> StructuralFingerprint:
        return compute_fingerprint(self.to_structure())

    def make_revision(self, *, revision_id: str, meta: Optional[Dict[str, Any]] = None) -> Revision:
        fp = self.fingerprint()
        return Revision(revision_id=revision_id, fingerprint=fp, meta=meta or {})

    def _build_graph(self) -> Dict[str, List[str]]:
        graph: Dict[str, List[str]] = {nid: [] for nid in self.node_ids}
        for ch in self.channels:
            if ch.src_node_id in graph and ch.dst_node_id in graph:
                graph[ch.src_node_id].append(ch.dst_node_id)
        return graph

    def _build_reverse_graph(self) -> Dict[str, List[str]]:
        reverse: Dict[str, List[str]] = {nid: [] for nid in self.node_ids}
        for ch in self.channels:
            if ch.src_node_id in reverse and ch.dst_node_id in reverse:
                reverse[ch.dst_node_id].append(ch.src_node_id)
        return reverse

    def execute(self, *, revision_id: str) -> ExecutionTrace:
        """Step45: DAG propagation (ALL_SUCCESS policy)."""
        from .validation.validator import ValidationEngine

        started_at = datetime.utcnow()
        execution_id = str(uuid.uuid4())

        validation = ValidationEngine().validate(self, revision_id=revision_id)

        node_traces: Dict[str, NodeTrace] = {
            nid: NodeTrace(
                node_id=nid,
                node_status=NodeStatus.NOT_REACHED,
                pre_status=StageStatus.SKIPPED,
                core_status=StageStatus.SKIPPED,
                post_status=StageStatus.SKIPPED,
            )
            for nid in self.node_ids
        }

        if validation.success and self.entry_node_id in node_traces:
            graph = self._build_graph()
            reverse = self._build_reverse_graph()

            # Mark entry SUCCESS
            node_traces[self.entry_node_id] = NodeTrace(
                node_id=self.entry_node_id,
                node_status=NodeStatus.SUCCESS,
                pre_status=StageStatus.SUCCESS,
                core_status=StageStatus.SUCCESS,
                post_status=StageStatus.SUCCESS,
            )

            # Simple BFS propagation under ALL_SUCCESS policy
            queue = [self.entry_node_id]

            while queue:
                current = queue.pop(0)
                for child in graph.get(current, []):
                    parents = reverse.get(child, [])
                    parent_statuses = [
                        node_traces[p].node_status for p in parents
                    ]

                    if all(s == NodeStatus.SUCCESS for s in parent_statuses):
                        node_traces[child] = NodeTrace(
                            node_id=child,
                            node_status=NodeStatus.SUCCESS,
                            pre_status=StageStatus.SUCCESS,
                            core_status=StageStatus.SUCCESS,
                            post_status=StageStatus.SUCCESS,
                        )
                        queue.append(child)
                    elif any(s == NodeStatus.FAILURE for s in parent_statuses):
                        node_traces[child] = NodeTrace(
                            node_id=child,
                            node_status=NodeStatus.SKIPPED,
                            pre_status=StageStatus.SKIPPED,
                            core_status=StageStatus.SKIPPED,
                            post_status=StageStatus.SKIPPED,
                        )

        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        trace = ExecutionTrace(
            execution_id=execution_id,
            revision_id=revision_id,
            structural_fingerprint=validation.structural_fingerprint,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            validation_success=validation.success,
            validation_violations=[(v.rule_id, v.message) for v in validation.violations],
            nodes=node_traces,
            meta={"engine_meta": self.meta},
            expected_node_ids=self.node_ids,
        )

        return trace
