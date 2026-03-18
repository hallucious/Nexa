from typing import Dict, Any, Set, List


ALLOWED_TOP_LEVEL = {
    "schema",
    "schema_version",
    "circuit_id",
    "title",
    "nodes",
    "edges",
    "entry_node_id",
    "exit_policy",
    "description",
    "tags",
    "meta",
}

ALLOWED_NODE_KEYS = {
    "id",
    "kind",
    "name",
    "stage_policy",
    "io",
    "bindings",
    "validation",
}

ALLOWED_EDGE_KEYS = {
    "from",
    "to",
    "kind",
    "priority",
    "condition",
}


def validate_circuit(data: Dict[str, Any]) -> None:
    _validate_required(data)
    _validate_unknown_fields(data)
    node_ids = _validate_nodes(data["nodes"])
    _validate_edges(data["edges"], node_ids)
    _validate_dag(data["edges"], node_ids)
    _validate_reachability(data["edges"], node_ids, data["entry_node_id"])


def _validate_required(data: Dict[str, Any]) -> None:
    required = [
        "schema",
        "schema_version",
        "circuit_id",
        "nodes",
        "edges",
        "entry_node_id",
        "exit_policy",
    ]
    for key in required:
        if key not in data:
            raise ValueError(f"Missing required field: {key}")


def _validate_unknown_fields(data: Dict[str, Any]) -> None:
    for key in data.keys():
        if key not in ALLOWED_TOP_LEVEL:
            raise ValueError(f"Unknown top-level field: {key}")


def _validate_nodes(nodes: List[Dict[str, Any]]) -> Set[str]:
    node_ids: Set[str] = set()
    for node in nodes:
        for k in node.keys():
            if k not in ALLOWED_NODE_KEYS:
                raise ValueError(f"Unknown node field: {k}")
        nid = node.get("id")
        if not nid:
            raise ValueError("Node missing id")
        if nid in node_ids:
            raise ValueError("Duplicate node id")
        node_ids.add(nid)
    return node_ids


def _validate_edges(edges: List[Dict[str, Any]], node_ids: Set[str]) -> None:
    for edge in edges:
        for k in edge.keys():
            if k not in ALLOWED_EDGE_KEYS:
                raise ValueError(f"Unknown edge field: {k}")
        if edge["from"] not in node_ids:
            raise ValueError("Edge from invalid node")
        if edge["to"] not in node_ids:
            raise ValueError("Edge to invalid node")


def _validate_dag(edges: List[Dict[str, Any]], node_ids: Set[str]) -> None:
    graph = {nid: [] for nid in node_ids}
    for e in edges:
        graph[e["from"]].append(e["to"])

    visited = set()
    stack = set()

    def dfs(n):
        if n in stack:
            raise ValueError("Cycle detected")
        if n in visited:
            return
        stack.add(n)
        for nxt in graph[n]:
            dfs(nxt)
        stack.remove(n)
        visited.add(n)

    for nid in node_ids:
        if nid not in visited:
            dfs(nid)


def _validate_reachability(edges: List[Dict[str, Any]], node_ids: Set[str], entry: str) -> None:
    graph = {nid: [] for nid in node_ids}
    for e in edges:
        graph[e["from"]].append(e["to"])

    reachable = set()

    def dfs(n):
        if n in reachable:
            return
        reachable.add(n)
        for nxt in graph[n]:
            dfs(nxt)

    dfs(entry)

    if reachable != node_ids:
        raise ValueError("Unreachable node detected")
