from src.circuit.model import CircuitModel, NodeModel, EdgeModel
from src.circuit.runtime_adapter import execute_circuit


def make_model_seq():
    nodes = {
        "n1": NodeModel(id="n1", raw={"id": "n1"}),
        "n2": NodeModel(id="n2", raw={"id": "n2"}),
    }
    edges = [EdgeModel(from_id="n1", to_id="n2", kind="next", raw={"from": "n1", "to": "n2", "kind": "next"})]
    return CircuitModel(circuit_id="c1", nodes=nodes, edges=edges, entry_node_id="n1", raw={})


def test_staged_handler_runs_pre_core_post_in_order_and_merges_patches():
    m = make_model_seq()
    order = []

    def pre(node_id, raw, inp):
        order.append(("pre", node_id, dict(inp)))
        return {"p": 1}

    def core(node_id, raw, inp):
        order.append(("core", node_id, dict(inp)))
        # ensure pre patch applied to core input
        assert inp.get("p") == 1
        return {"c": 2}

    def post(node_id, raw, out):
        order.append(("post", node_id, dict(out)))
        # ensure core output visible
        assert out.get("c") == 2
        return {"q": 3}

    handler = {"pre": pre, "core": core, "post": post}
    res = execute_circuit(m, handler)
    assert res == {"c": 2, "q": 3}
    # first node runs stages; second node has no edges from n2 so execution ends after n2.
    # Our handler runs for both nodes, but core for n2 will receive previous result.
    # For simplicity, check that we saw pre/core/post at least once for n1.
    assert order[0][0] == "pre"
    assert order[1][0] == "core"
    assert order[2][0] == "post"
