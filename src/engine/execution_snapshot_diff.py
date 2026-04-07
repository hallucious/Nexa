from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class NodeDiffResult:
    node_id: str
    output_changed: bool
    artifact_changed: bool
    hash_changed: bool
    metadata_changed: bool
    verifier_changed: bool = False


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
            verifier_a = getattr(node_a, "verifier_status", None), sorted(getattr(node_a, "verifier_reason_codes", []) or [])
            verifier_b = getattr(node_b, "verifier_status", None), sorted(getattr(node_b, "verifier_reason_codes", []) or [])
            if verifier_a == (None, []) and isinstance(getattr(node_a, "metadata", None), dict):
                meta_verifier = node_a.metadata.get("verifier")
                if isinstance(meta_verifier, dict):
                    verifier_a = meta_verifier.get("status"), sorted(meta_verifier.get("reason_codes") or [])
            if verifier_b == (None, []) and isinstance(getattr(node_b, "metadata", None), dict):
                meta_verifier = node_b.metadata.get("verifier")
                if isinstance(meta_verifier, dict):
                    verifier_b = meta_verifier.get("status"), sorted(meta_verifier.get("reason_codes") or [])
            verifier_changed = verifier_a != verifier_b

            if (
                output_changed
                or artifact_changed
                or hash_changed
                or metadata_changed
                or verifier_changed
            ):
                modified_nodes.append(
                    NodeDiffResult(
                        node_id=node_id,
                        output_changed=output_changed,
                        artifact_changed=artifact_changed,
                        hash_changed=hash_changed,
                        metadata_changed=metadata_changed,
                        verifier_changed=verifier_changed,
                    )
                )

        summary = {
            "total_nodes_a": len(nodes_a),
            "total_nodes_b": len(nodes_b),
            "added_count": len(added_nodes),
            "removed_count": len(removed_nodes),
            "modified_count": len(modified_nodes),
            "verifier_changed_count": sum(1 for node in modified_nodes if node.verifier_changed),
        }

        return ExecutionSnapshotDiffReport(
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            summary=summary,
        )