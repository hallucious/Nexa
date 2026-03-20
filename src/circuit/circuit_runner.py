from typing import Any, Dict, List, Set
import re
from concurrent.futures import ThreadPoolExecutor
import uuid

from src.circuit.circuit_scheduler import CircuitScheduler
from src.circuit.circuit_validator import CircuitValidator


NODE_OUTPUT_REF_PATTERN = re.compile(r"^node\.(?P<node_id>[A-Za-z0-9_]+)\.output(?:\.[A-Za-z0-9_]+)*$")
NODE_OUTPUT_SHORTHAND_PATTERN = re.compile(r"^(?P<node_id>[A-Za-z0-9_]+)\.output(?:\.[A-Za-z0-9_]+)*$")


def _extract_cross_node_refs(value: Any) -> Set[str]:
    refs: Set[str] = set()

    if isinstance(value, str):
        match = NODE_OUTPUT_REF_PATTERN.match(value) or NODE_OUTPUT_SHORTHAND_PATTERN.match(value)
        if match is not None:
            refs.add(match.group("node_id"))
        return refs

    if isinstance(value, dict):
        for item in value.values():
            refs.update(_extract_cross_node_refs(item))
        return refs

    if isinstance(value, list):
        for item in value:
            refs.update(_extract_cross_node_refs(item))
        return refs

    return refs



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

    def _validate_cross_node_references(self, circuit: Dict[str, Any]) -> None:
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        node_ids = {node.get("id") for node in nodes if node.get("id")}

        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue
            config_id = node.get("execution_config_ref")
            if not isinstance(config_id, str) or not config_id:
                continue
            config = self.registry.get(config_id)
            referenced_nodes = _extract_cross_node_refs(config)
            if not referenced_nodes:
                continue

            depends_on = set(node.get("depends_on", []))
            for referenced_node_id in sorted(referenced_nodes):
                if referenced_node_id == node_id:
                    raise ValueError(f"node cross-reference cannot target itself: {node_id}")
                if referenced_node_id not in node_ids:
                    raise ValueError(
                        f"node cross-reference points to unknown node: {node_id} -> {referenced_node_id}"
                    )
                if referenced_node_id not in depends_on:
                    raise ValueError(
                        f"node cross-reference missing depends_on: {node_id} requires {referenced_node_id}"
                    )

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
        current_state.setdefault("__node_outputs__", {})

        validator = CircuitValidator(nodes)
        validator.validate()
        self._validate_cross_node_references(circuit)

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
                    node_output = future.result()
                    current_state[node_id] = node_output
                    node_outputs = current_state.setdefault("__node_outputs__", {})
                    if isinstance(node_outputs, dict):
                        node_outputs[node_id] = node_output

        visible_state_keys = len([key for key in current_state if key != "__node_outputs__"])

        self._emit_runtime_event(
            "execution_completed",
            {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
                "executed_nodes": len(nodes),
                "state_keys": visible_state_keys,
            },
        )

        return current_state