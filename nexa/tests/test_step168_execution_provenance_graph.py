from src.engine.execution_provenance_graph import (
    ExecutionProvenanceGraphBuilder,
)


class FakeSnapshot:

    def __init__(self):

        self.nodes = {
            "node1": {
                "artifacts": ["artifactA"],
                "depends_on": []
            },
            "node2": {
                "artifacts": ["artifactB"],
                "depends_on": ["node1"]
            }
        }


def test_graph_build():

    snapshot = FakeSnapshot()

    graph = ExecutionProvenanceGraphBuilder.build(snapshot)

    assert "node1" in graph.nodes
    assert "node2" in graph.nodes


def test_artifact_node_creation():

    snapshot = FakeSnapshot()

    graph = ExecutionProvenanceGraphBuilder.build(snapshot)

    artifact_nodes = [n for n in graph.nodes if "artifact::" in n]

    assert len(artifact_nodes) == 2


def test_dependency_edge():

    snapshot = FakeSnapshot()

    graph = ExecutionProvenanceGraphBuilder.build(snapshot)

    deps = [
        e for e in graph.edges
        if e.relation == "depends_on"
    ]

    assert len(deps) == 1


def test_to_dict():

    snapshot = FakeSnapshot()

    graph = ExecutionProvenanceGraphBuilder.build(snapshot)

    d = ExecutionProvenanceGraphBuilder.to_dict(graph)

    assert "nodes" in d
    assert "edges" in d