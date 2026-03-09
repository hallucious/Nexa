from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class DummyProvider:
    def execute(self, request):
        return {"output": f"echo:{request.prompt}", "trace": {"provider": "dummy"}}


def test_step106_node_trace_observability_contract():
    registry = ProviderRegistry()
    registry.register("__legacy_provider__", DummyProvider())
    runtime = NodeExecutionRuntime(provider_executor=ProviderExecutor(registry))

    node = {"id": "n1", "prompt": "hello {name}"}
    state = {"name": "world"}

    result = runtime.execute(node, state)

    assert result.node_id == "n1"
    assert result.output == "echo:hello world"

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
