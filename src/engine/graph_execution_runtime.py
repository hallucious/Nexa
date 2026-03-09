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
        self.node_statuses = {}
        self.node_inputs = {}
        self.node_messages = {}

    def record(self, node_id: str, output=None, *, status="success", input_snapshot=None, message=None):
        if status == "success":
            idx = len(self.node_sequence)
            self.execution_index[node_id] = idx
            self.node_sequence.append(node_id)
        self.node_outputs[node_id] = output
        self.node_statuses[node_id] = status
        self.node_inputs[node_id] = input_snapshot
        self.node_messages[node_id] = message


class GraphResult:
    def __init__(self, state, artifacts, trace):
        self.state = state
        self.artifacts = artifacts
        self.trace = trace


class GraphExecutionRuntime:
    """
    Step129-A

    Preserve legacy constructor contract:
        GraphExecutionRuntime(node_runtime)

    Routing rules:
    - legacy node without execution_config_ref:
        pass through directly to node_runtime
    - node with execution_config_ref:
        requires node_spec_resolver and is resolved before execution
    """

    def __init__(self, node_runtime, node_spec_resolver=None):
        self.node_runtime = node_runtime
        self.node_spec_resolver = node_spec_resolver

    def execute(self, circuit: dict, state: dict):
        nodes = circuit.get("nodes", [])
        edges = circuit.get("edges", [])
        entry = circuit.get("entry")
        flow = circuit.get("flow", [])

        node_map = {n["id"]: n for n in nodes}
        order = self._topological_sort(nodes, edges)

        artifacts = []
        trace = GraphTrace()

        outgoing = defaultdict(list)
        reverse = defaultdict(list)
        indegree = {n["id"]: 0 for n in nodes}
        for e in edges:
            outgoing[e["from"]].append(e)
            reverse[e["to"]].append(e)
            indegree[e["to"]] = indegree.get(e["to"], 0) + 1

        flow_policy = {n["id"]: "ALL_SUCCESS" for n in nodes}
        for rule in flow:
            node_id = rule.get("node_id")
            policy = rule.get("policy")
            if node_id in flow_policy and policy:
                flow_policy[node_id] = str(policy)

        shared_state = dict(state)

        for node_id in order:
            node = node_map[node_id]
            parent_edges = reverse.get(node_id, [])
            parents = [edge["from"] for edge in parent_edges]

            should_run = False
            should_skip = False
            skip_message = None

            if not parents:
                if entry is None:
                    should_run = True
                else:
                    should_run = node_id == entry
            else:
                parent_statuses = [trace.node_statuses.get(parent, "not_reached") for parent in parents]
                policy = flow_policy.get(node_id, "ALL_SUCCESS")

                if policy == "ALL_SUCCESS":
                    if any(status in ("failure", "skipped") for status in parent_statuses):
                        should_skip = True
                        skip_message = "upstream failure prevents ALL_SUCCESS"
                    elif all(status == "success" for status in parent_statuses):
                        should_run = True
                elif policy in ("ANY_SUCCESS", "FIRST_SUCCESS"):
                    if any(status == "success" for status in parent_statuses):
                        should_run = True
                    elif all(status in ("failure", "skipped") for status in parent_statuses):
                        should_skip = True
                        skip_message = "no upstream success satisfies ANY_SUCCESS"
                else:
                    raise ValueError(f"Unknown flow policy: {policy}")

            if should_skip:
                trace.record(node_id, None, status="skipped", input_snapshot=None, message=skip_message)
                continue

            if not should_run:
                trace.record(node_id, None, status="not_reached", input_snapshot=None, message=None)
                continue

            execution_node = node
            if isinstance(node, dict) and "execution_config_ref" in node:
                if self.node_spec_resolver is None:
                    raise RuntimeError(
                        "NodeSpecResolver is required when graph node uses execution_config_ref"
                    )
                execution_node = self.node_spec_resolver.resolve(node)

            input_snapshot = dict(shared_state)
            for parent in parents:
                parent_output = trace.node_outputs.get(parent)
                if parent_output is not None:
                    input_snapshot[parent] = parent_output

            try:
                result = self.node_runtime.execute(
                    node=execution_node,
                    state=input_snapshot,
                )
            except Exception as exc:
                trace.record(node_id, None, status="failure", input_snapshot=input_snapshot, message=str(exc))
                continue

            if hasattr(result, "artifacts") and result.artifacts:
                artifacts.extend(result.artifacts)

            for edge in outgoing[node_id]:
                channel = edge["channel"]
                shared_state[channel] = getattr(result, "output", None)

            trace.record(
                node_id,
                getattr(result, "output", None),
                status="success",
                input_snapshot=input_snapshot,
                message=None,
            )

        trace.finished_at = datetime.now(timezone.utc)
        trace.duration_ms = int(
            (trace.finished_at - trace.started_at).total_seconds() * 1000
        )

        return GraphResult(
            state=shared_state,
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
