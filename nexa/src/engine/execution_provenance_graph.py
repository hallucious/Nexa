from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ProvenanceNode:
    id: str
    type: str
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProvenanceEdge:
    source: str
    target: str
    relation: str


@dataclass
class ExecutionProvenanceGraph:
    nodes: Dict[str, ProvenanceNode]
    edges: List[ProvenanceEdge]


class ExecutionProvenanceGraphBuilder:

    @staticmethod
    def build(snapshot) -> ExecutionProvenanceGraph:
        """
        Build a provenance graph from an execution snapshot.
        """

        nodes: Dict[str, ProvenanceNode] = {}
        edges: List[ProvenanceEdge] = []

        # snapshot.nodes expected structure:
        # {
        #   node_id: {
        #       "artifacts": [artifact_id...],
        #       "depends_on": [node_id...]
        #   }
        # }

        for node_id, node_data in snapshot.nodes.items():

            nodes[node_id] = ProvenanceNode(
                id=node_id,
                type="execution_node",
                label=node_id,
                metadata={}
            )

            # dependency edges
            for dep in node_data.get("depends_on", []):
                edges.append(
                    ProvenanceEdge(
                        source=dep,
                        target=node_id,
                        relation="depends_on",
                    )
                )

            # artifact edges
            for artifact in node_data.get("artifacts", []):
                artifact_id = f"artifact::{artifact}"

                if artifact_id not in nodes:
                    nodes[artifact_id] = ProvenanceNode(
                        id=artifact_id,
                        type="artifact_node",
                        label=artifact,
                        metadata={}
                    )

                edges.append(
                    ProvenanceEdge(
                        source=node_id,
                        target=artifact_id,
                        relation="produced",
                    )
                )

        return ExecutionProvenanceGraph(nodes=nodes, edges=edges)

    @staticmethod
    def to_dict(graph: ExecutionProvenanceGraph):

        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "metadata": n.metadata,
                }
                for n in graph.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                }
                for e in graph.edges
            ],
        }