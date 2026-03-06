
"""
Step115: Sequential GraphExecutionRuntime (MVP)

Features:
- Topological sort execution
- Sequential node execution
- Channel-based state propagation
- Artifact accumulation (append-only)
- Cycle detection (fail-fast)

This runtime expects a NodeExecutionRuntime-like object with:
    execute(node: dict, state: dict) -> result
where result has attributes:
    - output
    - artifacts (list)
"""

from collections import defaultdict, deque
from uuid import uuid4


class GraphCycleError(Exception):
    """Raised when a cycle is detected in the circuit graph."""
    pass


class GraphTrace:
    """Minimal graph execution trace."""

    def __init__(self):
        self.run_id = uuid4().hex
        self.node_sequence = []
        self.node_outputs = {}

    def record(self, node_id: str, output=None):
        self.node_sequence.append(node_id)
        self.node_outputs[node_id] = output


class GraphResult:
    """Final result of graph execution."""

    def __init__(self, state, artifacts, trace):
        self.state = state
        self.artifacts = artifacts
        self.trace = trace


class GraphExecutionRuntime:
    """
    Sequential GraphExecutionRuntime (Step115).
    NodeExecutionRuntime must be injected (dependency injection).
    """

    def __init__(self, node_runtime):
        self.node_runtime = node_runtime

    def execute(self, circuit: dict, state: dict):
        nodes = circuit.get("nodes", [])
        edges = circuit.get("edges", [])

        node_map = {n["id"]: n for n in nodes}

        order = self._topological_sort(nodes, edges)

        artifacts = []
        trace = GraphTrace()

        # build outgoing edge map
        outgoing = defaultdict(list)
        for e in edges:
            outgoing[e["from"]].append(e)

        for node_id in order:
            node = node_map[node_id]

            result = self.node_runtime.execute(
                node=node,
                state=state
            )

            # append artifacts
            if hasattr(result, "artifacts") and result.artifacts:
                artifacts.extend(result.artifacts)

            # propagate channels
            for edge in outgoing[node_id]:
                channel = edge["channel"]
                state[channel] = getattr(result, "output", None)

            trace.record(node_id, getattr(result, "output", None))

        return GraphResult(
            state=state,
            artifacts=artifacts,
            trace=trace
        )

    def _topological_sort(self, nodes, edges):
        """Kahn's algorithm for topological sorting."""
        node_ids = [n["id"] for n in nodes]

        indegree = {nid: 0 for nid in node_ids}
        adj = defaultdict(list)

        for e in edges:
            src = e["from"]
            dst = e["to"]
            adj[src].append(dst)
            indegree[dst] += 1

        queue = deque([nid for nid in node_ids if indegree[nid] == 0])
        order = []

        while queue:
            nid = queue.popleft()
            order.append(nid)

            for neighbor in adj[nid]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(node_ids):
            raise GraphCycleError("Cycle detected in circuit graph")

        return order
