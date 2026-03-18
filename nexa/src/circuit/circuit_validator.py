from typing import Dict, List, Any, Set


class CircuitValidationError(Exception):
    pass


class CircuitValidator:
    """
    Step140

    Validates circuit structure before execution.
    """

    def __init__(self, nodes: List[Dict[str, Any]]):

        self.nodes = nodes
        self.node_map = {}

    def validate(self):

        self._validate_duplicate_ids()
        self._validate_dependencies_exist()
        self._validate_no_cycles()
        self._validate_execution_refs()

    def _validate_duplicate_ids(self):

        seen = set()

        for node in self.nodes:

            node_id = node.get("id")

            if node_id is None:
                raise CircuitValidationError("node missing id")

            if node_id in seen:
                raise CircuitValidationError(f"duplicate node id: {node_id}")

            seen.add(node_id)

            self.node_map[node_id] = node

    def _validate_dependencies_exist(self):

        for node in self.nodes:

            for dep in node.get("depends_on", []):

                if dep not in self.node_map:
                    raise CircuitValidationError(
                        f"missing dependency: {dep}"
                    )

    def _validate_no_cycles(self):

        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node_id):

            if node_id in stack:
                raise CircuitValidationError(
                    f"cycle detected at node: {node_id}"
                )

            if node_id in visited:
                return

            stack.add(node_id)

            node = self.node_map[node_id]

            for dep in node.get("depends_on", []):
                dfs(dep)

            stack.remove(node_id)
            visited.add(node_id)

        for node_id in self.node_map:
            dfs(node_id)

    def _validate_execution_refs(self):

        for node in self.nodes:

            if "execution_config_ref" not in node:

                raise CircuitValidationError(
                    f"node missing execution_config_ref: {node.get('id')}"
                )