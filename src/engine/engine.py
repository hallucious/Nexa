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

    def execute(self, *, revision_id: str) -> ExecutionTrace:
        """Guarded execute() returning an immutable ExecutionTrace.

        Step44 (Minimal Execution Semantics v1.1.0):
        - If validation succeeds:
          - entry_node is marked SUCCESS with pre/core/post SUCCESS.
          - all other nodes remain NOT_REACHED.
        - If validation fails:
          - all nodes remain NOT_REACHED (validation-only trace).
        """
        from .validation.validator import ValidationEngine

        started_at = datetime.utcnow()
        execution_id = str(uuid.uuid4())

        validation = ValidationEngine().validate(self, revision_id=revision_id)

        # Initialize full node coverage (all NOT_REACHED by default)
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

        # Minimal semantics: mark entry as SUCCESS only if validation passed
        if validation.success and self.entry_node_id in node_traces:
            node_traces[self.entry_node_id] = NodeTrace(
                node_id=self.entry_node_id,
                node_status=NodeStatus.SUCCESS,
                pre_status=StageStatus.SUCCESS,
                core_status=StageStatus.SUCCESS,
                post_status=StageStatus.SUCCESS,
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
