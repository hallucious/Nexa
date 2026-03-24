from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class DummyProvider:
    def execute(self, request):
        return {"output": f"echo:{request.prompt}", "trace": {"provider": "dummy"}}


def test_step106_node_trace_observability_contract():
    registry = ProviderRegistry()
    registry.register("dummy", DummyProvider())
    runtime = NodeExecutionRuntime(provider_executor=ProviderExecutor(registry))

    config = {
        "config_id": "n1",
        "node_id": "n1",
        "prompt_ref": "basic",
        "provider_ref": "dummy",
        "runtime_config": {
            "return_raw_output": True,
            "write_observability": True,
        },
    }
    result = runtime.execute(config, {"name": "world"})

    assert result.node_id == "n1"
    trace = result.trace

    assert "prompt_render" in trace.events
    assert "provider_execute" in trace.events
    assert "prompt_render" in trace.timings_ms
    assert "provider_execute" in trace.timings_ms
    assert trace.provider_trace["provider"] == "dummy"
