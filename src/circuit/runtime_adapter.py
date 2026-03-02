from typing import Callable, Dict, Any
from .model import CircuitModel


def execute_circuit(model: CircuitModel, engine_executor: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    current_id = model.entry_node_id
    visited = set()

    while True:
        if current_id in visited:
            raise ValueError("Unexpected cycle during execution")
        visited.add(current_id)

        node = model.nodes[current_id]
        result = engine_executor(current_id, node.raw)

        next_edges = [
            e for e in model.edges
            if e.from_id == current_id and e.kind == "next"
        ]

        other_edges = [
            e for e in model.edges
            if e.from_id == current_id and e.kind != "next"
        ]

        if other_edges:
            raise ValueError("Unsupported edge type in Phase1")

        if not next_edges:
            return result

        if len(next_edges) > 1:
            raise ValueError("Multiple next edges not supported in Phase1")

        current_id = next_edges[0].to_id
