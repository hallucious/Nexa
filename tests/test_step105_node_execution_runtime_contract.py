from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class DummyProvider:
    def execute(self, request):
        return {"output": f"echo:{request.prompt}", "trace": {"provider": "dummy"}}


def test_step105_node_execution_runtime_contract():
    registry = ProviderRegistry()
    registry.register("__legacy_provider__", DummyProvider())
    runtime = NodeExecutionRuntime(provider_executor=ProviderExecutor(registry))

    node = {"id": "n1", "prompt": "hello {name}"}
    state = {"name": "world"}

    result = runtime.execute(node, state)

    assert result.node_id == "n1"
    assert result.output == "echo:hello world"
    assert isinstance(result.artifacts, list)
    if result.artifacts:
        art = result.artifacts[0]
        assert getattr(art, "type", None) in ("provider_output", "output")
        assert getattr(art, "producer_node", None) in (None, "n1")
