import pytest

from src.engine.execution_snapshot_diff import (
    ExecutionSnapshotDiffEngine,
)


class FakeNode:
    def __init__(self, output, artifacts, output_hash, metadata):
        self.output = output
        self.artifacts = artifacts
        self.output_hash = output_hash
        self.metadata = metadata


class FakeSnapshot:
    def __init__(self, nodes):
        self.nodes = nodes


def test_same_snapshot_no_diff():

    node = FakeNode("hello", {}, "hash1", {})

    A = FakeSnapshot({"node1": node})
    B = FakeSnapshot({"node1": node})

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.added_nodes == []
    assert diff.removed_nodes == []
    assert diff.modified_nodes == []


def test_node_added():

    node = FakeNode("hello", {}, "hash1", {})

    A = FakeSnapshot({"node1": node})
    B = FakeSnapshot(
        {
            "node1": node,
            "node2": node,
        }
    )

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.added_nodes == ["node2"]


def test_node_removed():

    node = FakeNode("hello", {}, "hash1", {})

    A = FakeSnapshot(
        {
            "node1": node,
            "node2": node,
        }
    )

    B = FakeSnapshot({"node1": node})

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.removed_nodes == ["node2"]


def test_output_changed():

    nodeA = FakeNode("hello", {}, "hash1", {})
    nodeB = FakeNode("hello world", {}, "hash2", {})

    A = FakeSnapshot({"node1": nodeA})
    B = FakeSnapshot({"node1": nodeB})

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.modified_nodes[0].output_changed is True


def test_artifact_changed():

    nodeA = FakeNode("hello", {"a": 1}, "hash1", {})
    nodeB = FakeNode("hello", {"a": 2}, "hash1", {})

    A = FakeSnapshot({"node1": nodeA})
    B = FakeSnapshot({"node1": nodeB})

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.modified_nodes[0].artifact_changed is True


def test_hash_changed():

    nodeA = FakeNode("hello", {}, "hash1", {})
    nodeB = FakeNode("hello", {}, "hash2", {})

    A = FakeSnapshot({"node1": nodeA})
    B = FakeSnapshot({"node1": nodeB})

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.modified_nodes[0].hash_changed is True


def test_metadata_changed():

    nodeA = FakeNode("hello", {}, "hash1", {"a": 1})
    nodeB = FakeNode("hello", {}, "hash1", {"a": 2})

    A = FakeSnapshot({"node1": nodeA})
    B = FakeSnapshot({"node1": nodeB})

    diff = ExecutionSnapshotDiffEngine.compare(A, B)

    assert diff.modified_nodes[0].metadata_changed is True