# tests/test_step170_execution_debugger.py

from src.engine.execution_debugger import ExecutionDebugger


def make_run_data_success():
    return {
        "run_id": "run-1",
        "timeline": [
            {"event": "node_start", "node_id": "n1", "ts": "t1"},
            {"event": "node_finish", "node_id": "n1", "ts": "t2"},
            {"event": "node_start", "node_id": "n2", "ts": "t3"},
            {"event": "node_finish", "node_id": "n2", "ts": "t4"},
        ],
        "nodes": {
            "n1": {
                "status": "success",
                "inputs": ["a0"],
                "outputs": ["a1"],
            },
            "n2": {
                "status": "success",
                "inputs": ["a1"],
                "outputs": ["a2"],
            },
        },
        "artifacts": {
            "a0": {
                "producer": None,
                "depends_on": [],
            },
            "a1": {
                "producer": "n1",
                "depends_on": ["a0"],
            },
            "a2": {
                "producer": "n2",
                "depends_on": ["a1"],
            },
        },
        "provenance": {},
    }


def make_run_data_missing_artifact():
    return {
        "run_id": "run-2",
        "timeline": [
            {"event": "node_start", "node_id": "n1", "ts": "t1"},
            {"event": "node_failed", "node_id": "n1", "ts": "t2"},
        ],
        "nodes": {
            "n1": {
                "status": "failed",
                "inputs": ["missing_artifact"],
                "outputs": [],
            }
        },
        "artifacts": {},
        "provenance": {},
    }


def test_trace_node_success():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.trace_node(run, "n1")

    assert result["found"] is True
    assert result["node_id"] == "n1"
    assert result["summary"]["started"] is True
    assert result["summary"]["finished"] is True
    assert result["summary"]["failed"] is False


def test_trace_node_not_found():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.trace_node(run, "unknown")

    assert result["found"] is False
    assert result["reason"] == "node_not_found"


def test_trace_artifact_success():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.trace_artifact(run, "a1")

    assert result["found"] is True
    assert result["produced_by"] == "n1"
    assert "n2" in result["downstream_nodes"]


def test_trace_artifact_not_found():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.trace_artifact(run, "missing")

    assert result["found"] is False
    assert result["reason"] == "artifact_not_found"


def test_inspect_timeline_counts_events():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.inspect_timeline(run)

    assert result["event_count"] == 4
    assert result["summary"]["nodes_started"] == 2
    assert result["summary"]["nodes_finished"] == 2


def test_analyze_failure_no_failure():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.analyze_failure(run)

    assert result["has_failure"] is False
    assert result["summary"]["failed_node_count"] == 0


def test_analyze_failure_missing_artifact():
    dbg = ExecutionDebugger()
    run = make_run_data_missing_artifact()

    result = dbg.analyze_failure(run)

    assert result["has_failure"] is True
    assert result["failed_nodes"][0]["reason_code"] == "missing_input_artifact"


def test_dependency_path_success():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.dependency_path(run, "a2")

    assert result["found"] is True
    assert result["summary"]["hop_count"] > 0


def test_dependency_path_not_found():
    dbg = ExecutionDebugger()
    run = make_run_data_success()

    result = dbg.dependency_path(run, "unknown")

    assert result["found"] is False
    assert result["reason"] == "artifact_not_found"