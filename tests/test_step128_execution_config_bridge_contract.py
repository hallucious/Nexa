"""
Step128-B contract test

Goal:
Ensure that when a node contains `execution_config_ref`,
GraphExecutionRuntime still executes successfully and
passes the node through the runtime path.

This does NOT enforce resolver yet. It only ensures
the bridge path works without breaking existing behavior.
"""

import pytest


class _FakeNodeResult:
    def __init__(self, node_id):
        self.node_id = node_id
        self.output = {"ok": True}
        self.artifacts = []
        self.trace = None


class _FakeNodeRuntime:
    def __init__(self):
        self.last_node = None

    def execute(self, node, state):
        self.last_node = node
        return _FakeNodeResult(node.get("id"))


def test_step128_execution_config_ref_bridge():
    from src.engine.graph_execution_runtime import GraphExecutionRuntime

    runtime = _FakeNodeRuntime()
    engine = GraphExecutionRuntime(runtime)

    circuit = {
        "nodes": [
            {
                "id": "n1",
                "execution_config_ref": "ec_testhash"
            }
        ],
        "edges": []
    }

    result = engine.execute(circuit, state={})

    assert result.trace.node_sequence == ["n1"]
    assert runtime.last_node["execution_config_ref"] == "ec_testhash"
