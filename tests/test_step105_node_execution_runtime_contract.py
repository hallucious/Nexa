from src.engine.node_execution_runtime import NodeExecutionRuntime


class DummyProviderExecution:
    def execute(self, prompt):
        return {"output": f"echo:{prompt}"}


def test_step105_node_execution_runtime_contract():
    runtime = NodeExecutionRuntime(provider_execution=DummyProviderExecution())

    node = {"id": "n1", "prompt": "hello {name}"}
    state = {"name": "world"}

    result = runtime.execute(node, state)

    assert result.node_id == "n1"
    assert result.output == "echo:hello world"
    assert result.artifacts == []
    assert len(result.trace.events) >= 3