from src.engine.execution_diff_visualizer import ExecutionDiffVisualizer
from src.engine.execution_snapshot_diff import (
    ExecutionSnapshotDiffReport,
    NodeDiffResult,
)


def test_render_empty_diff():

    report = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[],
        summary={
            "total_nodes_a": 1,
            "total_nodes_b": 1,
            "added_count": 0,
            "removed_count": 0,
            "modified_count": 0,
        },
    )

    output = ExecutionDiffVisualizer.render(report)

    assert "Execution Diff Report" in output
    assert "modified: 0" in output


def test_render_added_node():

    report = ExecutionSnapshotDiffReport(
        added_nodes=["node3"],
        removed_nodes=[],
        modified_nodes=[],
        summary={
            "total_nodes_a": 2,
            "total_nodes_b": 3,
            "added_count": 1,
            "removed_count": 0,
            "modified_count": 0,
        },
    )

    output = ExecutionDiffVisualizer.render(report)

    assert "Nodes Added" in output
    assert "node3" in output


def test_render_modified_node():

    diff = NodeDiffResult(
        node_id="node1",
        output_changed=True,
        artifact_changed=False,
        hash_changed=True,
        metadata_changed=False,
    )

    report = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[diff],
        summary={
            "total_nodes_a": 1,
            "total_nodes_b": 1,
            "added_count": 0,
            "removed_count": 0,
            "modified_count": 1,
        },
    )

    output = ExecutionDiffVisualizer.render(report)

    assert "Nodes Modified" in output
    assert "node1" in output
    assert "output changed" in output
    assert "hash mismatch" in output


def test_render_removed_node():

    report = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=["node2"],
        modified_nodes=[],
        summary={
            "total_nodes_a": 3,
            "total_nodes_b": 2,
            "added_count": 0,
            "removed_count": 1,
            "modified_count": 0,
        },
    )

    output = ExecutionDiffVisualizer.render(report)

    assert "Nodes Removed" in output
    assert "node2" in output