from typing import Any, Dict, List

from src.circuit.circuit_scheduler import CircuitScheduler


class CircuitRunner:
    """
    Step137 + Step138

    Executes circuit nodes by:
    1. building DAG execution order from circuit nodes
    2. resolving each node's execution_config_ref
    3. calling NodeExecutionRuntime through execute_by_config_id()

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

    def execute(self, circuit: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        current_state = dict(state)

        scheduler = CircuitScheduler(nodes)
        execution_order = scheduler.topological_sort()

        for node_id in execution_order:
            node = scheduler.nodes[node_id]

            if "execution_config_ref" not in node:
                raise ValueError(f"node missing execution_config_ref: {node_id}")

            config_id = node["execution_config_ref"]

            result = self.runtime.execute_by_config_id(
                self.registry,
                config_id,
                current_state,
            )

            current_state[node_id] = result.output

        return current_state