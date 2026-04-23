
"""
Step129-B Contract Test
execution_config_ref nodes must use NodeSpecResolver
"""

import pytest


class FakeRuntime:
    def execute(self, node, state):
        return type("R", (), {"output": None, "artifacts": []})()


def test_step129_execution_config_requires_resolver():
    from src.engine.graph_execution_runtime import GraphExecutionRuntime

    circuit = {
        "nodes": [
            {
                "id": "n1",
                "execution_config_ref": "ec_testhash"
            }
        ],
        "edges": []
    }

    engine = GraphExecutionRuntime(node_runtime=FakeRuntime())

    with pytest.raises(RuntimeError):
        engine.execute(circuit, state={})
