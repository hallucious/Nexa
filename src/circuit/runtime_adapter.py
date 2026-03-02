from typing import Callable, Dict, Any
from .model import CircuitModel
from .condition_eval import evaluate


def execute_circuit(model: CircuitModel, engine_executor: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    current_id = model.entry_node_id
    visited = set()
    last_result: Dict[str, Any] = {}

    while True:
        if current_id in visited:
            raise ValueError("Unexpected cycle during execution")
        visited.add(current_id)

        node = model.nodes[current_id]
        last_result = engine_executor(current_id, node.raw)

        edges_from = [e for e in model.edges if e.from_id == current_id]

        next_edges = [e for e in edges_from if e.kind == "next"]
        conditional_edges = [e for e in edges_from if e.kind == "conditional"]
        other_edges = [e for e in edges_from if e.kind not in {"next", "conditional"}]

        if other_edges:
            raise ValueError("Unsupported edge type in Phase2")

        if len(next_edges) > 1:
            raise ValueError("Multiple next edges not supported")

        if next_edges:
            current_id = next_edges[0].to_id
            continue

        if conditional_edges:
            # priority required
            for e in conditional_edges:
                if "priority" not in e.raw:
                    raise ValueError("Conditional edge missing priority")

            conditional_edges = sorted(conditional_edges, key=lambda e: e.raw["priority"])

            for e in conditional_edges:
                cond = e.raw.get("condition", {})
                expr = cond.get("expr")
                if expr is None:
                    raise ValueError("Conditional edge missing expr")
                if evaluate(expr, last_result):
                    current_id = e.to_id
                    break
            else:
                return last_result
            continue

        return last_result
