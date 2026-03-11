from typing import Dict, List, Any
from collections import defaultdict, deque


class CircuitScheduler:
    """
    Step139

    DAG scheduler that produces execution waves.
    """

    def __init__(self, nodes: List[Dict[str, Any]]):

        self.nodes = {n["id"]: n for n in nodes}

    def execution_waves(self) -> List[List[str]]:

        in_degree = defaultdict(int)
        graph = defaultdict(list)

        for node_id, node in self.nodes.items():

            for dep in node.get("depends_on", []):
                graph[dep].append(node_id)
                in_degree[node_id] += 1

        queue = deque()

        for node_id in self.nodes:
            if in_degree[node_id] == 0:
                queue.append(node_id)

        waves = []

        while queue:

            wave_size = len(queue)
            wave = []

            for _ in range(wave_size):

                node = queue.popleft()
                wave.append(node)

                for nxt in graph[node]:

                    in_degree[nxt] -= 1

                    if in_degree[nxt] == 0:
                        queue.append(nxt)

            waves.append(wave)

        return waves