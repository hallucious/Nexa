from src.engine.execution_determinism_validator import (
    ExecutionDeterminismValidator,
)
from src.engine.execution_replay import ReplayNodeResult, ReplayResult


def test_step161_determinism_validator_success():
    replay = ReplayResult(
        execution_id="exec-1",
        success=True,
        node_results=[
            ReplayNodeResult(node_id="node_a", success=True, output="output-a"),
            ReplayNodeResult(node_id="node_b", success=True, output="output-b"),
        ],
    )

    validator = ExecutionDeterminismValidator()
    report = validator.validate(
        execution_id="exec-1",
        expected_outputs={
            "node_a": "output-a",
            "node_b": "output-b",
        },
        replay_result=replay,
    )

    assert report.execution_id == "exec-1"
    assert report.deterministic is True
    assert len(report.node_results) == 2
    assert report.node_results[0].deterministic is True
    assert report.node_results[1].deterministic is True


def test_step161_determinism_validator_output_mismatch():
    replay = ReplayResult(
        execution_id="exec-2",
        success=True,
        node_results=[
            ReplayNodeResult(node_id="node_a", success=True, output="wrong-output"),
        ],
    )

    validator = ExecutionDeterminismValidator()
    report = validator.validate(
        execution_id="exec-2",
        expected_outputs={
            "node_a": "expected-output",
        },
        replay_result=replay,
    )

    assert report.execution_id == "exec-2"
    assert report.deterministic is False
    assert len(report.node_results) == 1
    assert report.node_results[0].node_id == "node_a"
    assert report.node_results[0].deterministic is False
    assert report.node_results[0].reason == "output mismatch"


def test_step161_determinism_validator_missing_node_in_replay():
    replay = ReplayResult(
        execution_id="exec-3",
        success=True,
        node_results=[],
    )

    validator = ExecutionDeterminismValidator()
    report = validator.validate(
        execution_id="exec-3",
        expected_outputs={
            "node_a": "output-a",
        },
        replay_result=replay,
    )

    assert report.execution_id == "exec-3"
    assert report.deterministic is False
    assert len(report.node_results) == 1
    assert report.node_results[0].node_id == "node_a"
    assert report.node_results[0].deterministic is False
    assert report.node_results[0].reason == "node missing in replay"


def test_step161_determinism_validator_replay_failure():
    replay = ReplayResult(
        execution_id="exec-4",
        success=False,
        node_results=[
            ReplayNodeResult(
                node_id="node_a",
                success=False,
                output=None,
                error="runtime error",
            ),
        ],
    )

    validator = ExecutionDeterminismValidator()
    report = validator.validate(
        execution_id="exec-4",
        expected_outputs={
            "node_a": "output-a",
        },
        replay_result=replay,
    )

    assert report.execution_id == "exec-4"
    assert report.deterministic is False
    assert len(report.node_results) == 1
    assert report.node_results[0].node_id == "node_a"
    assert report.node_results[0].deterministic is False
    assert report.node_results[0].reason == "runtime error"