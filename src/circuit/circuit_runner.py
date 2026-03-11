from typing import Dict, Any, List


class CircuitRunner:
    """
    Step137

    Executes circuit nodes using NodeExecutionRuntime.
    """

    def __init__(self, runtime, registry):
        self.runtime = runtime
        self.registry = registry

    def execute(self, circuit: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:

        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        current_state = dict(state)

        for node in nodes:

            node_id = node.get("id")

            if "execution_config_ref" not in node:
                raise ValueError(f"node missing execution_config_ref: {node_id}")

            config_id = node["execution_config_ref"]

            result = self.runtime.execute_by_config_id(
                self.registry,
                config_id,
                current_state
            )

            current_state[node_id] = result.output

        return current_state