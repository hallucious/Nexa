from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor

from src.circuit.circuit_scheduler import CircuitScheduler
from src.circuit.circuit_validator import CircuitValidator


class CircuitRunner:
    """
    Step140

    Executes circuit nodes by:
    1. validating circuit structure
    2. building DAG execution waves
    3. resolving each node's execution_config_ref
    4. calling NodeExecutionRuntime through execute_by_config_id()
    5. storing each node output into shared state

    Circuit node shape:
    {
        "id": "node_id",
        "execution_config_ref": "config.id",
        "depends_on": ["upstream_node_id"]
    }
    """

    def __init__(self, runtime, registry):
        self.runtime = runtime
        self.registry = registry

    def _execute_node(self, node: Dict[str, Any], state: Dict[str, Any]):
        if "execution_config_ref" not in node:
            raise ValueError(f"node missing execution_config_ref: {node.get('id')}")

        config_id = node["execution_config_ref"]

        result = self.runtime.execute_by_config_id(
            self.registry,
            config_id,
            state,
        )

        return result.output

    def execute(self, circuit: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        current_state = dict(state)

        validator = CircuitValidator(nodes)
        validator.validate()

        scheduler = CircuitScheduler(nodes)
        waves = scheduler.execution_waves()

        for wave in waves:
            with ThreadPoolExecutor() as executor:
                futures = {}

                for node_id in wave:
                    node = scheduler.nodes[node_id]
                    futures[node_id] = executor.submit(
                        self._execute_node,
                        node,
                        current_state,
                    )

                for node_id, future in futures.items():
                    current_state[node_id] = future.result()

        return current_state