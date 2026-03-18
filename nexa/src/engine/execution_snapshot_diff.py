from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class NodeDiffResult:
    node_id: str
    output_changed: bool
    artifact_changed: bool
    hash_changed: bool
    metadata_changed: bool


@dataclass
class ExecutionSnapshotDiffReport:
    added_nodes: List[str]
    removed_nodes: List[str]
    modified_nodes: List[NodeDiffResult]
    summary: Dict[str, Any]


class ExecutionSnapshotDiffEngine:
    """
    Compare two execution snapshots and produce a diff report.
    """

    @staticmethod
    def compare(snapshot_a, snapshot_b) -> ExecutionSnapshotDiffReport:
        nodes_a = snapshot_a.nodes
        nodes_b = snapshot_b.nodes

        set_a = set(nodes_a.keys())
        set_b = set(nodes_b.keys())

        added_nodes = list(set_b - set_a)
        removed_nodes = list(set_a - set_b)
        common_nodes = set_a & set_b

        modified_nodes: List[NodeDiffResult] = []

        for node_id in common_nodes:

            node_a = nodes_a[node_id]
            node_b = nodes_b[node_id]

            output_changed = node_a.output != node_b.output
            artifact_changed = node_a.artifacts != node_b.artifacts
            hash_changed = node_a.output_hash != node_b.output_hash
            metadata_changed = node_a.metadata != node_b.metadata

            if (
                output_changed
                or artifact_changed
                or hash_changed
                or metadata_changed
            ):
                modified_nodes.append(
                    NodeDiffResult(
                        node_id=node_id,
                        output_changed=output_changed,
                        artifact_changed=artifact_changed,
                        hash_changed=hash_changed,
                        metadata_changed=metadata_changed,
                    )
                )

        summary = {
            "total_nodes_a": len(nodes_a),
            "total_nodes_b": len(nodes_b),
            "added_count": len(added_nodes),
            "removed_count": len(removed_nodes),
            "modified_count": len(modified_nodes),
        }

        return ExecutionSnapshotDiffReport(
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            summary=summary,
        )