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


def test_conditional_branch_A():
    model = make_model()
    def executor(node_id, raw):
        if node_id == "n1":
            return {"result": "A"}
        return {"final": node_id}

    result = execute_circuit(model, executor)
    assert result["final"] == "n2"


def test_conditional_no_match():
    model = make_model()
    def executor(node_id, raw):
        return {"result": "Z"}

    result = execute_circuit(model, executor)
    assert result["result"] == "Z"
