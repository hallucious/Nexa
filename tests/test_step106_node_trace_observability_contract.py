from src.engine.node_execution_runtime import NodeExecutionRuntime


class DummyProviderExecution:
    def execute(self, prompt):
        return {
            "output": f"echo:{prompt}",
            "trace": {"provider": "dummy"}
        }


def test_step106_node_trace_observability_contract():
    runtime = NodeExecutionRuntime(provider_execution=DummyProviderExecution())

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