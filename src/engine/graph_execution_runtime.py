"""
Step128-C

GraphExecutionRuntime now routes nodes with
`execution_config_ref` through NodeSpecResolver.

Legacy nodes still use the old execution path.
"""

from collections import defaultdict, deque
from datetime import datetime, timezone
from uuid import uuid4


class GraphCycleError(Exception):
    pass


class GraphTrace:
    def __init__(self):
        self.run_id = uuid4().hex
        self.started_at = datetime.now(timezone.utc)
        self.finished_at = None
        self.duration_ms = None
        self.node_sequence = []
        self.node_outputs = {}
        self.execution_index = {}

    def record(self, node_id: str, output=None):
        idx = len(self.node_sequence)
        self.execution_index[node_id] = idx
        self.node_sequence.append(node_id)
        self.node_outputs[node_id] = output


class GraphResult:
    def __init__(self, state, artifacts, trace):
        self.state = state
        self.artifacts = artifacts
        self.trace = trace


class GraphExecutionRuntime:
    def __init__(self, node_runtime, node_spec_resolver=None):
        self.node_runtime = node_runtime
        self.node_spec_resolver = node_spec_resolver

    def execute(self, circuit: dict, state: dict):
        nodes = circuit.get("nodes", [])
        edges = circuit.get("edges", [])

        node_map = {n["id"]: n for n in nodes}
        order = self._topological_sort(nodes, edges)

        artifacts = []
        trace = GraphTrace()

        outgoing = defaultdict(list)
        for e in edges:
            outgoing[e["from"]].append(e)

        for node_id in order:
            node = node_map[node_id]

            # Step128-C path routing
            execution_node = node

            if (
                self.node_spec_resolver
                and isinstance(node, dict)
                and "execution_config_ref" in node
            ):
                resolved = self.node_spec_resolver.resolve(node)
                execution_node = resolved

            result = self.node_runtime.execute(
                node=execution_node,
                state=state,
            )

            if hasattr(result, "artifacts") and result.artifacts:
                artifacts.extend(result.artifacts)

            for edge in outgoing[node_id]:
                channel = edge["channel"]
                state[channel] = getattr(result, "output", None)

            trace.record(node_id, getattr(result, "output", None))

        trace.finished_at = datetime.now(timezone.utc)
        trace.duration_ms = int(
            (trace.finished_at - trace.started_at).total_seconds() * 1000
        )

        return GraphResult(
            state=state,
            artifacts=artifacts,
            trace=trace,
        )

    def _topological_sort(self, nodes, edges):
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
