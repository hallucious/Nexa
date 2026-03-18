from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor
import uuid

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

    def _emit_runtime_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        *,
        node_id: str = None,
    ) -> None:
        emit_fn = getattr(self.runtime, "_emit_event", None)
        if callable(emit_fn):
            emit_fn(event_type, payload, node_id=node_id)

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

    def run_single_node(
        self,
        *,
        circuit: Dict[str, Any],
        node_id: str,
        state: Dict[str, Any],
    ):
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])

        target_node = None
        for node in nodes:
            if node.get("id") == node_id:
                target_node = node
                break

        if target_node is None:
            raise ValueError(f"node not found in circuit: {node_id}")

        return self._execute_node(target_node, state)

    def execute(self, circuit: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        current_state = dict(state)

        validator = CircuitValidator(nodes)
        validator.validate()

        scheduler = CircuitScheduler(nodes)
        waves = scheduler.execution_waves()

        circuit_id = circuit.get("id")
        execution_id = str(uuid.uuid4())

        set_execution_id = getattr(self.runtime, "set_execution_id", None)
        if callable(set_execution_id):
            set_execution_id(execution_id)

        self._emit_runtime_event(
            "execution_started",
            {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
            },
        )

        for wave_index, wave in enumerate(waves):
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

        self._emit_runtime_event(
            "execution_completed",
            {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
                "executed_nodes": len(nodes),
                "state_keys": len(current_state),
            },
        )

        return current_state