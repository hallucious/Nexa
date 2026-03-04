from src.engine.node_execution_runtime import NodeExecutionRuntime


class DummyProviderExecution:
    def execute(self, prompt):
        return {"output": f"echo:{prompt}"}


def test_step105_node_execution_runtime_contract():
    """Step105 baseline contract updated for Step108 artifact schema.

    Step105 originally asserted artifacts == []. From Step108 onward, NodeExecutionRuntime
    may emit a primary Artifact for the provider output. The stable guarantees are:
    - node_id/output correctness
    - artifacts is a list (may be empty or non-empty depending on runtime version)
    - trace is present
    """
    runtime = NodeExecutionRuntime(provider_execution=DummyProviderExecution())

    node = {"id": "n1", "prompt": "hello {name}"}
    state = {"name": "world"}

    result = runtime.execute(node, state)

    assert result.node_id == "n1"
    assert result.output == "echo:hello world"

    # Backward/forward compatible assertion
    assert isinstance(result.artifacts, list)

    # If artifacts are emitted, the first one should describe the primary output.
    if result.artifacts:
        art = result.artifacts[0]
        assert getattr(art, "type", None) in ("provider_output", "output")
        assert getattr(art, "producer_node", None) in (None, "n1")
