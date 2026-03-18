from src.engine.execution_audit_pack import (
    ExecutionAuditPackBuilder,
)
from src.engine.execution_snapshot_diff import (
    ExecutionSnapshotDiffReport,
)
from src.engine.execution_regression_detector import (
    ExecutionRegressionReport,
)


class FakeSnapshot:
    pass


def test_build_audit_pack():

    snapshot = FakeSnapshot()

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[],
        summary={},
    )

    regression = ExecutionRegressionReport(
        regressions=[],
        total_regressions=0,
        highest_severity="LOW",
    )

    metadata = {
        "run_id": "run_test",
        "node_count": 1,
    }

    pack = ExecutionAuditPackBuilder.build(
        snapshot,
        diff,
        "diff text",
        regression,
        metadata,
    )

    assert pack.metadata["run_id"] == "run_test"
    assert pack.diff_visualization == "diff text"


def test_audit_pack_to_dict():

    snapshot = FakeSnapshot()

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[],
        summary={},
    )

    regression = ExecutionRegressionReport(
        regressions=[],
        total_regressions=0,
        highest_severity="LOW",
    )

    metadata = {
        "run_id": "run_test",
    }

    pack = ExecutionAuditPackBuilder.build(
        snapshot,
        diff,
        "diff text",
        regression,
        metadata,
    )

    d = ExecutionAuditPackBuilder.to_dict(pack)

    assert "metadata" in d
    assert "snapshot" in d
    assert "diff" in d
    assert "diff_text" in d
    assert "regression" in d


def test_regression_integration():

    snapshot = FakeSnapshot()

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[],
        summary={},
    )

    regression = ExecutionRegressionReport(
        regressions=[],
        total_regressions=0,
        highest_severity="LOW",
    )

    metadata = {}

    pack = ExecutionAuditPackBuilder.build(
        snapshot,
        diff,
        "visual",
        regression,
        metadata,
    )

    assert pack.regression_report.total_regressions == 0


def test_visualization_integration():

    snapshot = FakeSnapshot()

    diff = ExecutionSnapshotDiffReport(
        added_nodes=[],
        removed_nodes=[],
        modified_nodes=[],
        summary={},
    )

    regression = ExecutionRegressionReport(
        regressions=[],
        total_regressions=0,
        highest_severity="LOW",
    )

    metadata = {}

    pack = ExecutionAuditPackBuilder.build(
        snapshot,
        diff,
        "visual text",
        regression,
        metadata,
    )

    assert pack.diff_visualization == "visual text"