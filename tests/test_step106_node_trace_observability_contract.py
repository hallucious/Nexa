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
    state = {"name": "world"}

    result = runtime.execute(config, state)

    assert result.node_id == "n1"

    trace = result.trace

    assert "pre_plugins" in trace.events
    assert "prompt_render" in trace.events
    assert "provider_execute" in trace.events
    assert "post_plugins" in trace.events

    assert "pre_plugins" in trace.timings_ms
    assert "prompt_render" in trace.timings_ms
    assert "provider_execute" in trace.timings_ms
    assert "post_plugins" in trace.timings_ms

    assert trace.provider_trace["provider"] == "dummy"
    assert "noop_pre_plugin" in trace.plugin_trace["pre"]
    assert "noop_post_plugin" in trace.plugin_trace["post"]
