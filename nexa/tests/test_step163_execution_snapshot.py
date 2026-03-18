from src.engine.execution_artifact_hashing import ExecutionHashBuilder
from src.engine.execution_snapshot import ExecutionSnapshotBuilder
from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan


def test_step163_execution_snapshot_builds_successfully():
    timeline = ExecutionTimeline(
        execution_id="exec-1",
        start_ms=0,
        end_ms=100,
        duration_ms=100,
        node_spans=[
            NodeExecutionSpan(
                node_id="node_a",
                start_ms=10,
                end_ms=30,
                duration_ms=20,
                status="success",
            ),
            NodeExecutionSpan(
                node_id="node_b",
                start_ms=40,
                end_ms=80,
                duration_ms=40,
                status="success",
            ),
        ],
    )

    outputs = {
        "node_a": {"value": 1},
        "node_b": {"value": 2},
    }

    hash_builder = ExecutionHashBuilder()
    hash_report = hash_builder.build(
        execution_id="exec-1",
        outputs=outputs,
    )

    snapshot_builder = ExecutionSnapshotBuilder()
    snapshot = snapshot_builder.build(
        execution_id="exec-1",
        timeline=timeline,
        outputs=outputs,
        hash_report=hash_report,
    )

    assert snapshot.execution_id == "exec-1"
    assert snapshot.timeline.execution_id == "exec-1"
    assert snapshot.node_outputs == outputs
    assert len(snapshot.node_hashes) == 2
    assert snapshot.node_hashes[0].node_id == "node_a"
    assert snapshot.node_hashes[1].node_id == "node_b"


def test_step163_execution_snapshot_rejects_timeline_execution_id_mismatch():
    timeline = ExecutionTimeline(
        execution_id="exec-timeline",
        start_ms=0,
        end_ms=10,
        duration_ms=10,
        node_spans=[
            NodeExecutionSpan(
                node_id="node_a",
                start_ms=1,
                end_ms=5,
                duration_ms=4,
                status="success",
            ),
        ],
    )

    outputs = {
        "node_a": {"value": 1},
    }

    hash_builder = ExecutionHashBuilder()
    hash_report = hash_builder.build(
        execution_id="exec-1",
        outputs=outputs,
    )

    snapshot_builder = ExecutionSnapshotBuilder()

    try:
        snapshot_builder.build(
            execution_id="exec-1",
            timeline=timeline,
            outputs=outputs,
            hash_report=hash_report,
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "timeline" in str(exc)


def test_step163_execution_snapshot_rejects_hash_report_execution_id_mismatch():
    timeline = ExecutionTimeline(
        execution_id="exec-1",
        start_ms=0,
        end_ms=10,
        duration_ms=10,
        node_spans=[
            NodeExecutionSpan(
                node_id="node_a",
                start_ms=1,
                end_ms=5,
                duration_ms=4,
                status="success",
            ),
        ],
    )

    outputs = {
        "node_a": {"value": 1},
    }

    hash_builder = ExecutionHashBuilder()
    hash_report = hash_builder.build(
        execution_id="exec-hash",
        outputs=outputs,
    )

    snapshot_builder = ExecutionSnapshotBuilder()

    try:
        snapshot_builder.build(
            execution_id="exec-1",
            timeline=timeline,
            outputs=outputs,
            hash_report=hash_report,
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "hash report" in str(exc)