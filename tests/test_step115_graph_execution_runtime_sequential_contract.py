
"""
Step115 Contract Test
Sequential GraphExecutionRuntime
"""

import pytest


class FakeNodeResult:
    def __init__(self, output):
        self.output = output
        self.artifacts = [f"artifact:{output}"]


class FakeNodeRuntime:
    def execute(self, node, state):
        node_id = node["id"]

        if node_id == "analysis":
            return FakeNodeResult("analysis_result")

        if node_id == "answer":
            return FakeNodeResult(f"answer_using_{state.get('analysis')}")

        return FakeNodeResult("unknown")


def test_step115_sequential_graph_execution():
    from src.engine.graph_execution_runtime import GraphExecutionRuntime

    circuit = {
        "nodes": [
            {"id": "analysis", "prompt": "Analyze {{question}}"},
            {"id": "answer", "prompt": "Answer using {{analysis}}"},
        ],
        "edges": [
            {"from": "analysis", "to": "answer", "channel": "analysis"}
        ],
        "entry": "analysis"
    }

    state = {
        "question": "Why is the sky blue?"
    }

    runtime = GraphExecutionRuntime(node_runtime=FakeNodeRuntime())

    result = runtime.execute(circuit=circuit, state=state)

    # execution order
    assert result.trace.node_sequence == ["analysis", "answer"]

    # channel propagation
    assert result.state["analysis"] == "analysis_result"

    # artifact accumulation
    assert len(result.artifacts) >= 2


def test_step115_cycle_fail_fast():
    from src.engine.graph_execution_runtime import GraphExecutionRuntime, GraphCycleError

    circuit = {
        "nodes": [
            {"id": "a"},
            {"id": "b"},
        ],
        "edges": [
            {"from": "a", "to": "b", "channel": "x"},
            {"from": "b", "to": "a", "channel": "y"},
        ],
        "entry": "a"
    }

    runtime = GraphExecutionRuntime(node_runtime=FakeNodeRuntime())

    with pytest.raises(GraphCycleError):
        runtime.execute(circuit=circuit, state={})
