from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor

from src.circuit.circuit_scheduler import CircuitScheduler


class CircuitRunner:

    def __init__(self, runtime, registry):
        self.runtime = runtime
        self.registry = registry

    def _execute_node(self, node, state):

        config_id = node["execution_config_ref"]

        result = self.runtime.execute_by_config_id(
            self.registry,
            config_id,
            state
        )

        return result.output

    def execute(self, circuit: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:

        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])

        current_state = dict(state)

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
                        current_state
                    )

                for node_id, future in futures.items():

                    current_state[node_id] = future.result()

        return current_state