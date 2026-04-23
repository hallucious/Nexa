from src.circuit.runtime_adapter import execute_circuit
from src.circuit.model import CircuitModel, NodeModel, EdgeModel


def make_model_seq():
    nodes = {"n1": NodeModel("n1", {"id": "n1"}), "n2": NodeModel("n2", {"id": "n2"})}
    edges = [EdgeModel("n1", "n2", "next", {"from": "n1", "to": "n2", "kind": "next"})]
    return CircuitModel("c1", nodes, edges, "n1", {})


def test_trace_off_default_no_trace_key():
    m = make_model_seq()

    def ex(node_id, raw):
        return {"last": node_id}

    res = execute_circuit(m, ex)
    assert res["last"] == "n2"
    assert "trace" not in m.raw


def test_trace_on_records_nodes_order():
    m = make_model_seq()
    m.raw["trace_enabled"] = True

    def ex(node_id, raw):
        return {"last": node_id}

    res = execute_circuit(m, ex)
    assert res["last"] == "n2"
    assert "trace" in m.raw
    tr = m.raw["trace"]
    assert [nt.node_id for nt in tr.nodes] == ["n1", "n2"]
