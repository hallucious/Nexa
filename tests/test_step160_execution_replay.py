from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_replay import (
    ExecutionReplayEngine,
    ReplayPlanner,
)
from src.engine.execution_timeline import (
    ExecutionTimeline,
    NodeExecutionSpan,
)


class DummyRegistry:
    def __init__(self):
        self._configs = {
            "cfg.a": {"config_id": "cfg.a"},
            "cfg.b": {"config_id": "cfg.b"},
        }

    def get(self, config_id):
        return self._configs[config_id]


class DummyRuntime:
    def execute_by_config_id(self, registry, config_id, state):
        class Result:
            def __init__(self, output):
                self.output = output

        outputs = {
            "cfg.a": "output-a",
            "cfg.b": "output-b",
        }
        return Result(outputs[config_id])


def test_step160_replay_planner_builds_node_order():
    timeline = ExecutionTimeline(
        execution_id="exec-1",
        start_ms=0,
        end_ms=100,
        duration_ms=100,
        node_spans=[
            NodeExecutionSpan(
                node_id="node_b",
                start_ms=20,
                end_ms=40,
                duration_ms=20,
                status="success",
            ),
            NodeExecutionSpan(
                node_id="node_a",
                start_ms=10,
                end_ms=15,
                duration_ms=5,
                status="success",
            ),
        ],
    )

    planner = ReplayPlanner()
    plan = planner.build_plan(timeline)

    assert plan.execution_id == "exec-1"
    assert plan.node_order == ["node_a", "node_b"]


def test_step160_replay_engine_replays_node_outputs():
    runtime = DummyRuntime()
    registry = DummyRegistry()
    runner = CircuitRunner(runtime, registry)

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {
                "id": "node_a",
                "execution_config_ref": "cfg.a",
                "depends_on": [],
            },
            {
                "id": "node_b",
                "execution_config_ref": "cfg.b",
                "depends_on": ["node_a"],
            },
        ],
    }

    timeline = ExecutionTimeline(
        execution_id="exec-2",
        start_ms=0,
        end_ms=50,
        duration_ms=50,
        node_spans=[
            NodeExecutionSpan(
                node_id="node_a",
                start_ms=10,
                end_ms=20,
                duration_ms=10,
                status="success",
            ),
            NodeExecutionSpan(
                node_id="node_b",
                start_ms=25,
                end_ms=40,
                duration_ms=15,
                status="success",
            ),
        ],
    )

    planner = ReplayPlanner()
    plan = planner.build_plan(timeline)

    engine = ExecutionReplayEngine()
    result = engine.replay(
        plan=plan,
        circuit_runner=runner,
        circuit=circuit,
        input_state={"question": "x"},
        expected_outputs={
            "node_a": "output-a",
            "node_b": "output-b",
        },
    )

    assert result.execution_id == "exec-2"
    assert result.success is True
    assert len(result.node_results) == 2
    assert result.node_results[0].node_id == "node_a"
    assert result.node_results[0].success is True
    assert result.node_results[0].output == "output-a"
    assert result.node_results[1].node_id == "node_b"
    assert result.node_results[1].success is True
    assert result.node_results[1].output == "output-b"


def test_step160_replay_engine_detects_output_mismatch():
    runtime = DummyRuntime()
    registry = DummyRegistry()
    runner = CircuitRunner(runtime, registry)

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {
                "id": "node_a",
                "execution_config_ref": "cfg.a",
                "depends_on": [],
            },
        ],
    }

    timeline = ExecutionTimeline(
        execution_id="exec-3",
        start_ms=0,
        end_ms=20,
        duration_ms=20,
        node_spans=[
            NodeExecutionSpan(
                node_id="node_a",
                start_ms=10,
                end_ms=15,
                duration_ms=5,
                status="success",
            ),
        ],
    )

    planner = ReplayPlanner()
    plan = planner.build_plan(timeline)

    engine = ExecutionReplayEngine()
    result = engine.replay(
        plan=plan,
        circuit_runner=runner,
        circuit=circuit,
        input_state={},
        expected_outputs={
            "node_a": "wrong-output",
        },
    )

    assert result.execution_id == "exec-3"
    assert result.success is False
    assert len(result.node_results) == 1
    assert result.node_results[0].node_id == "node_a"
    assert result.node_results[0].success is False
    assert "replay output mismatch" in result.node_results[0].error