from src.engine.execution_diff_visualizer import ExecutionDiffVisualizer
from src.engine.execution_snapshot_diff import ExecutionSnapshotDiffEngine


class FakeNode:
    def __init__(self, output, artifacts=None, output_hash="", metadata=None, verifier_status=None, verifier_reason_codes=None):
        self.output = output
        self.artifacts = artifacts or {}
        self.output_hash = output_hash
        self.metadata = metadata or {}
        self.verifier_status = verifier_status
        self.verifier_reason_codes = verifier_reason_codes or []


class FakeSnapshot:
    def __init__(self, nodes):
        self.nodes = nodes


def test_step209_legacy_execution_snapshot_diff_detects_verifier_change() -> None:
    left = FakeSnapshot({
        "node1": FakeNode("hello", {}, "hash1", {}, verifier_status="warning", verifier_reason_codes=["R1"])
    })
    right = FakeSnapshot({
        "node1": FakeNode("hello", {}, "hash1", {}, verifier_status="pass", verifier_reason_codes=[])
    })

    diff = ExecutionSnapshotDiffEngine.compare(left, right)

    assert diff.modified_nodes[0].verifier_changed is True
    assert diff.summary["verifier_changed_count"] == 1

    rendered = ExecutionDiffVisualizer.render(diff)
    assert "verifier changed" in rendered
    assert "verifier_changed: 1" in rendered
