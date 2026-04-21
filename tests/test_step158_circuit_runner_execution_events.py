from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_event_emitter import ExecutionEventEmitter


class DummyRegistry:
    def __init__(self):
        self._configs = {
            "cfg.a": {"config_id": "cfg.a"},
            "cfg.b": {"config_id": "cfg.b"},
        }

    def get(self, config_id):
        return self._configs[config_id]


class DummyRuntime:
    def __init__(self):
        self.event_emitter = ExecutionEventEmitter(event_file=None)
        self.execution_id = "runtime-default"

    def set_execution_id(self, execution_id):
        self.execution_id = execution_id

    def _emit_event(self, event_type, payload, node_id=None):
        from src.contracts.execution_event_contract import ExecutionEvent

        self.event_emitter.emit(
            ExecutionEvent.now(
                event_type,
                payload,
                execution_id=self.execution_id,
                node_id=node_id,
            )
        )

    def execute_by_config_id(self, registry, config_id, state):
        class Result:
            def __init__(self, output):
                self.output = output

        return Result(output=f"done:{config_id}")


def test_step158_circuit_runner_emits_execution_started_and_completed():
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

    result = runner.execute(circuit, {"input_value": "x"})

    assert result["node_a"] == "done:cfg.a"
    assert result["node_b"] == "done:cfg.b"

    events = runtime.event_emitter.get_events()
    assert len(events) == 2

    started = events[0]
    completed = events[1]

    assert started.type == "execution_started"
    assert started.node_id is None
    assert started.execution_id == completed.execution_id
    assert started.payload["circuit_id"] == "sample-circuit"
    assert started.payload["execution_id"] == started.execution_id
    assert started.payload["total_nodes"] == 2
    assert started.payload["total_waves"] == 2

    assert completed.type == "execution_completed"
    assert completed.node_id is None
    assert completed.execution_id == started.execution_id
    assert completed.payload["circuit_id"] == "sample-circuit"
    assert completed.payload["execution_id"] == completed.execution_id
    assert completed.payload["total_nodes"] == 2
    assert completed.payload["total_waves"] == 2
    assert completed.payload["executed_nodes"] == 2
    assert completed.payload["state_keys"] == 3