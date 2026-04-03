from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_replay import (
    ExecutionReplayEngine,
    ReplayPlan,
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


class InspectingRuntime:
    def __init__(self):
        self.inputs = []

    def execute_by_config_id(self, registry, config_id, state):
        self.inputs.append((config_id, dict(state)))

        class Result:
            def __init__(self, output):
                self.output = output

        if config_id == "cfg.a":
            return Result("output-a")

        return Result(state.get("analysis", state.get("node_a", "missing-input")))


class FailingAfterFirstRuntime:
    def execute_by_config_id(self, registry, config_id, state):
        class Result:
            def __init__(self, output):
                self.output = output

        if config_id == "cfg.a":
            raise RuntimeError("boom-a")
        return Result("output-b")



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


def test_step160_replay_engine_propagates_edge_channel_state_to_next_node():
    runtime = InspectingRuntime()
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
        "edges": [
            {"from": "node_a", "to": "node_b", "channel": "analysis"},
        ],
    }

    timeline = ExecutionTimeline(
        execution_id="exec-channel",
        start_ms=0,
        end_ms=50,
        duration_ms=50,
        node_spans=[
            NodeExecutionSpan(node_id="node_a", start_ms=10, end_ms=20, duration_ms=10, status="success"),
            NodeExecutionSpan(node_id="node_b", start_ms=25, end_ms=40, duration_ms=15, status="success"),
        ],
    )

    plan = ReplayPlanner().build_plan(timeline)
    result = ExecutionReplayEngine().replay(
        plan=plan,
        circuit_runner=runner,
        circuit=circuit,
        input_state={"question": "x"},
        expected_outputs={
            "node_a": "output-a",
            "node_b": "output-a",
        },
    )

    assert result.success is True
    assert runtime.inputs[1][1]["analysis"] == "output-a"
    assert runtime.inputs[1][1]["node_a"] == "output-a"


def test_step160_replay_engine_marks_downstream_failure_when_parent_output_missing():
    runtime = FailingAfterFirstRuntime()
    registry = DummyRegistry()
    runner = CircuitRunner(runtime, registry)

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {"id": "node_a", "execution_config_ref": "cfg.a", "depends_on": []},
            {"id": "node_b", "execution_config_ref": "cfg.b", "depends_on": ["node_a"]},
        ],
        "edges": [
            {"from": "node_a", "to": "node_b", "channel": "analysis"},
        ],
    }

    timeline = ExecutionTimeline(
        execution_id="exec-fail",
        start_ms=0,
        end_ms=50,
        duration_ms=50,
        node_spans=[
            NodeExecutionSpan(node_id="node_a", start_ms=10, end_ms=20, duration_ms=10, status="failure"),
            NodeExecutionSpan(node_id="node_b", start_ms=25, end_ms=40, duration_ms=15, status="not_reached"),
        ],
    )

    plan = ReplayPlanner().build_plan(timeline)
    result = ExecutionReplayEngine().replay(
        plan=plan,
        circuit_runner=runner,
        circuit=circuit,
        input_state={},
        expected_outputs={
            "node_a": "output-a",
            "node_b": "output-b",
        },
    )

    assert result.success is False
    assert result.node_results[0].node_id == "node_a"
    assert result.node_results[0].success is False
    assert "boom-a" in result.node_results[0].error
    assert result.node_results[1].node_id == "node_b"
    assert result.node_results[1].success is False
    assert "missing parent outputs" in result.node_results[1].error


def test_step160_replay_engine_empty_plan_is_success():
    result = ExecutionReplayEngine().replay(
        plan=ReplayPlan(execution_id="exec-empty", node_order=[]),
        circuit_runner=object(),
        circuit={"id": "empty", "nodes": []},
        input_state={},
        expected_outputs=None,
    )

    assert result.execution_id == "exec-empty"
    assert result.success is True
    assert result.node_results == []


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
