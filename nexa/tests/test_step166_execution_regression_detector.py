from src.engine.execution_regression_detector import (
    ExecutionRegressionDetector,
)
from src.engine.execution_snapshot_diff import (
    ExecutionSnapshotDiffReport,
    NodeDiffResult,
)


def test_removed_node_regression():

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=["node2"],
        modified_nodes=[],
        summary={},
    )

    report = ExecutionRegressionDetector.detect(diff)

    assert report.total_regressions == 1
    assert report.regressions[0].type == "NODE_REMOVED"
    assert report.highest_severity == "HIGH"


def test_output_changed_regression():

    diff_node = NodeDiffResult(
        node_id="node1",
        output_changed=True,
        artifact_changed=False,
        hash_changed=False,
        metadata_changed=False,
    )

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[diff_node],
        summary={},
    )

    report = ExecutionRegressionDetector.detect(diff)

    assert report.total_regressions == 1
    assert report.regressions[0].type == "OUTPUT_CHANGED"
    assert report.highest_severity == "MEDIUM"


def test_hash_mismatch_regression():

    diff_node = NodeDiffResult(
        node_id="node1",
        output_changed=False,
        artifact_changed=False,
        hash_changed=True,
        metadata_changed=False,
    )

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[diff_node],
        summary={},
    )

    report = ExecutionRegressionDetector.detect(diff)

    assert report.regressions[0].type == "HASH_MISMATCH"
    assert report.highest_severity == "HIGH"


def test_metadata_regression():

    diff_node = NodeDiffResult(
        node_id="node1",
        output_changed=False,
        artifact_changed=False,
        hash_changed=False,
        metadata_changed=True,
    )

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[diff_node],
        summary={},
    )

    report = ExecutionRegressionDetector.detect(diff)

    assert report.regressions[0].type == "METADATA_CHANGED"
    assert report.highest_severity == "LOW"


def test_no_regression():

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[],
        summary={},
    )

    report = ExecutionRegressionDetector.detect(diff)

    assert report.total_regressions == 0