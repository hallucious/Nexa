import pytest
from src.circuit.runtime_adapter import execute_circuit
from src.circuit.model import CircuitModel, NodeModel, EdgeModel


def make_model():
    nodes = {
        "n1": NodeModel("n1", {"id": "n1"}),
        "n2": NodeModel("n2", {"id": "n2"}),
    }
    edges = [
        EdgeModel("n1", "n2", "next", {"from": "n1", "to": "n2", "kind": "next"})
    ]
    return CircuitModel("c1", nodes, edges, "n1", {})


def test_sequential_execution():
    model = make_model()
    order = []

    def executor(node_id, raw):
        order.append(node_id)
        return {"last": node_id}

    result = execute_circuit(model, executor)
    assert order == ["n1", "n2"]
    assert result["last"] == "n2"


def test_multiple_next_not_allowed():
    model = make_model()
    model.edges.append(
        EdgeModel("n1", "n2", "next", {"from": "n1", "to": "n2", "kind": "next"})
    )

    with pytest.raises(ValueError):
        execute_circuit(model, lambda a, b: {})
