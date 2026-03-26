from src.circuit.circuit_runner import CircuitRunner
from src.platform.execution_config_registry import AdhocExecutionConfigRegistry


class DummyRuntime:

    def execute_by_config_id(self, registry, config_id, state):
        class R:
            output = f"ran:{config_id}"
        return R()


def test_step137_circuit_runtime_bridge():

    registry = AdhocExecutionConfigRegistry()

    registry.register({
        "config_id": "qa.answer"
    })

    runtime = DummyRuntime()

    runner = CircuitRunner(runtime, registry)

    circuit = {
        "nodes": [
            {
                "id": "node1",
                "execution_config_ref": "qa.answer"
            }
        ]
    }

    state = {"question": "hi"}

    result = runner.execute(circuit, state)

    assert result["node1"] == "ran:qa.answer"