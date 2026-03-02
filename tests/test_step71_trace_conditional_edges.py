from src.circuit.runtime_adapter import execute_circuit
from src.circuit.model import CircuitModel, NodeModel, EdgeModel

def make_model():
    nodes = {
        "n1": NodeModel("n1", {"id": "n1"}),
        "n2": NodeModel("n2", {"id": "n2"}),
        "n3": NodeModel("n3", {"id": "n3"}),
    }
    edges = [
        EdgeModel("n1", "n2", "conditional", {
            "from": "n1",
            "to": "n2",
            "kind": "conditional",
            "priority": 1,
            "condition": {"expr": 'eq("result","A")'}
        }),
        EdgeModel("n1", "n3", "conditional", {
            "from": "n1",
            "to": "n3",
            "kind": "conditional",
            "priority": 2,
            "condition": {"expr": 'eq("result","B")'}
        }),
    ]
    return CircuitModel("c1", nodes, edges, "n1", {})

def test_trace_records_selected_edge_and_condition_for_match():
    model = make_model()
    model.raw["trace_enabled"] = True

    def executor(node_id, raw):
        if node_id == "n1":
            return {"result": "A"}
        return {"final": node_id}

    res = execute_circuit(model, executor)
    assert res["final"] == "n2"
    tr = model.raw["trace"]
    # first node trace corresponds to n1
    nt = tr.nodes[0]
    assert nt.node_id == "n1"
    assert nt.selected_edge is not None
    assert nt.selected_edge.to_node_id == "n2"
    assert nt.selected_edge.priority == 1
    assert nt.condition_result is not None
    assert nt.condition_result.expression == 'eq("result","A")'
    assert nt.condition_result.value is True
    assert nt.condition_result.error is None

def test_trace_records_last_condition_when_no_match_and_no_selected_edge():
    model = make_model()
    model.raw["trace_enabled"] = True

    def executor(node_id, raw):
        return {"result": "Z"}

    res = execute_circuit(model, executor)
    assert res["result"] == "Z"
    tr = model.raw["trace"]
    nt = tr.nodes[0]
    assert nt.node_id == "n1"
    assert nt.selected_edge is None
    assert nt.condition_result is not None
    # last evaluated condition is priority 2
    assert nt.condition_result.expression == 'eq("result","B")'
    assert nt.condition_result.value is False
