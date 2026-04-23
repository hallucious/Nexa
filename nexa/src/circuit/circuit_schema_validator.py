from __future__ import annotations

from typing import Any, Dict, Set


class CircuitSchemaValidationError(ValueError):
    """Raised when a .nex circuit file fails static schema validation."""


class CircuitSchemaValidator:
    """
    Step155

    Performs compile-time/static schema validation for .nex circuit files.

    Scope:
    - root object shape
    - nodes presence/type
    - node field shape
    - depends_on type
    - unknown field rejection

    Out of scope:
    - duplicate ids
    - missing dependency targets
    - cycle detection

    Those remain the responsibility of CircuitValidator.
    """

    ROOT_ALLOWED_FIELDS: Set[str] = {"id", "version", "metadata", "nodes"}
    NODE_ALLOWED_FIELDS: Set[str] = {"id", "execution_config_ref", "depends_on", "metadata"}

    def __init__(self, circuit: Any):
        self.circuit = circuit

    def validate(self) -> Dict[str, Any]:
        if not isinstance(self.circuit, dict):
            raise CircuitSchemaValidationError("circuit root must be an object")

        self._validate_root_fields(self.circuit)
        self._validate_nodes(self.circuit)
        return self.circuit

    def _validate_root_fields(self, circuit: Dict[str, Any]) -> None:
        unknown = sorted(set(circuit.keys()) - self.ROOT_ALLOWED_FIELDS)
        if unknown:
            raise CircuitSchemaValidationError(
                f"circuit contains unsupported root field(s): {', '.join(unknown)}"
            )

    def _validate_nodes(self, circuit: Dict[str, Any]) -> None:
        if "nodes" not in circuit:
            raise CircuitSchemaValidationError("circuit missing required field: nodes")

        nodes = circuit["nodes"]
        if not isinstance(nodes, list):
            raise CircuitSchemaValidationError("circuit field 'nodes' must be a list")

        for index, node in enumerate(nodes):
            self._validate_node(index, node)

    def _validate_node(self, index: int, node: Any) -> None:
        if not isinstance(node, dict):
            raise CircuitSchemaValidationError(
                f"circuit node at index {index} must be an object"
            )

        unknown = sorted(set(node.keys()) - self.NODE_ALLOWED_FIELDS)
        if unknown:
            raise CircuitSchemaValidationError(
                f"circuit node at index {index} contains unsupported field(s): {', '.join(unknown)}"
            )

        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise CircuitSchemaValidationError(
                f"circuit node at index {index} missing valid string field: id"
            )

        execution_config_ref = node.get("execution_config_ref")
        if not isinstance(execution_config_ref, str) or not execution_config_ref.strip():
            raise CircuitSchemaValidationError(
                f"circuit node '{node_id}' missing valid string field: execution_config_ref"
            )

        depends_on = node.get("depends_on", [])
        if not isinstance(depends_on, list):
            raise CircuitSchemaValidationError(
                f"circuit node '{node_id}' field 'depends_on' must be a list"
            )

        for dep_index, dep in enumerate(depends_on):
            if not isinstance(dep, str) or not dep.strip():
                raise CircuitSchemaValidationError(
                    f"circuit node '{node_id}' has invalid depends_on entry at index {dep_index}"
                )