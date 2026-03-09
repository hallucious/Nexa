from __future__ import annotations

from src.engine.graph_execution_runtime import GraphExecutionRuntime


class _Result:
    def __init__(self, output):
        self.output = output
        self.artifacts = []


class _Runtime:
    def execute(self, node, state):
        node_id = node["id"]
        if node_id == "e":
            return _Result({})
        if node_id == "a":
            raise RuntimeError("boom")
        if node_id == "b":
            return _Result({"ok": True})
        if node_id == "c":
            assert state["b"]["ok"] is True
            return _Result({"done": True})
        return _Result({})


def _circuit(policy: str):
    return {
        "entry": "e",
        "nodes": [{"id": "e"}, {"id": "a"}, {"id": "b"}, {"id": "c"}],
        "edges": [
            {"from": "e", "to": "a", "channel": "c_e_a"},
            {"from": "e", "to": "b", "channel": "c_e_b"},
            {"from": "a", "to": "c", "channel": "c_a_c"},
            {"from": "b", "to": "c", "channel": "c_b_c"},
        ],
        "flow": [{"rule_id": "fr_c", "node_id": "c", "policy": policy}],
    }


def test_step130_graph_runtime_any_success_runs_downstream_on_partial_parent_failure():
    runtime = GraphExecutionRuntime(node_runtime=_Runtime())
    result = runtime.execute(_circuit("ANY_SUCCESS"), state={})

    assert result.trace.node_statuses["a"] == "failure"
    assert result.trace.node_statuses["b"] == "success"
    assert result.trace.node_statuses["c"] == "success"
    assert result.trace.node_inputs["c"]["b"] == {"ok": True}


def test_step130_graph_runtime_all_success_skips_downstream_when_any_parent_fails():
    runtime = GraphExecutionRuntime(node_runtime=_Runtime())
    result = runtime.execute(_circuit("ALL_SUCCESS"), state={})

    assert result.trace.node_statuses["a"] == "failure"
    assert result.trace.node_statuses["b"] == "success"
    assert result.trace.node_statuses["c"] == "skipped"
