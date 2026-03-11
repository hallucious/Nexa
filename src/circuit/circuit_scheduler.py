from typing import Dict, List, Any


class CircuitScheduler:
    """
    Step138

    DAG scheduler for circuit execution.
    """

    def __init__(self, nodes: List[Dict[str, Any]]):

        self.nodes = {n["id"]: n for n in nodes}

    def topological_sort(self) -> List[str]:

        visited = set()
        order = []

        def dfs(node_id):

            if node_id in visited:
                return

            visited.add(node_id)

            node = self.nodes[node_id]

            for dep in node.get("depends_on", []):
                dfs(dep)

            order.append(node_id)

        for node_id in self.nodes:
            dfs(node_id)

        return order