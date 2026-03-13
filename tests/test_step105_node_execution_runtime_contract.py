from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class DummyProvider:
    def execute(self, request):
        return {"output": f"echo:{request.prompt}", "trace": {"provider": "dummy"}}


def test_step105_node_execution_runtime_contract():
    registry = ProviderRegistry()
    registry.register("dummy", DummyProvider())
    runtime = NodeExecutionRuntime(provider_executor=ProviderExecutor(registry))

    config = {
        "config_id": "n1",
        "node_id": "n1",
        "provider_ref": "dummy",
        "runtime_config": {
            "return_raw_output": True,
            "write_observability": True,
        },
    }
    state = {"name": "world"}

    result = runtime.execute(config, state)

    assert result.node_id == "n1"
    assert isinstance(result.output, str)
    assert result.output.startswith("echo:")
    assert isinstance(result.artifacts, list)
    if result.artifacts:
        art = result.artifacts[0]
        assert getattr(art, "type", None) in ("provider_output", "output")
        assert getattr(art, "producer_node", None) in (None, "n1")
