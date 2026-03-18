from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.engine.execution_artifact_hashing import ExecutionHashReport, NodeOutputHash
from src.engine.execution_timeline import ExecutionTimeline


@dataclass
class ExecutionSnapshot:
    execution_id: str
    timeline: ExecutionTimeline
    node_outputs: Dict[str, Any]
    node_hashes: List[NodeOutputHash]


class ExecutionSnapshotBuilder:
    """
    Build an execution snapshot from timeline + outputs + hash report.

    v1 scope:
    - store execution_id
    - store execution timeline
    - store node outputs
    - store node hashes
    """

    def build(
        self,
        *,
        execution_id: str,
        timeline: ExecutionTimeline,
        outputs: Dict[str, Any],
        hash_report: ExecutionHashReport,
    ) -> ExecutionSnapshot:
        if execution_id != timeline.execution_id:
            raise ValueError("execution_id mismatch between snapshot and timeline")

        if execution_id != hash_report.execution_id:
            raise ValueError("execution_id mismatch between snapshot and hash report")

        return ExecutionSnapshot(
            execution_id=execution_id,
            timeline=timeline,
            node_outputs=dict(outputs),
            node_hashes=list(hash_report.node_hashes),
        )