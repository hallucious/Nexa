"""
test_step135 — Runtime is graph-only. Anti-regression guard.

1. Runtime executes plugins only via dependency graph.
2. pre_plugins/post_plugins constructor kwargs are rejected (removed from interface).
"""
import pytest
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.platform.plugin_result import PluginResult


class RecordingProvider:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {"output": f"provider:{request.prompt}", "trace": {"provider": "recording"}}


def test_step135_runtime_is_graph_only(tmp_path):
    """Graph-based plugin execution produces correct output and trace events."""
    registry = ProviderRegistry()
    registry.register("openai", RecordingProvider())
    called = []

    def search(query):
        called.append("graph")
        return PluginResult(output={"result": f"search:{query}"})

    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        plugin_registry={"search": search},
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_graph_only",
        "plugins": [{"plugin_id": "search", "inputs": {"query": "input.query"}, "output_fields": ["result"]}],
    }

    result = runtime.execute(config, {"query": "nexa"})
    assert result.output == "search:nexa"
    assert called == ["graph"]
    assert any(e.startswith("plugin_execute:search") for e in result.trace.events)
    assert any(e.startswith("wave:") for e in result.trace.events)


def test_step135_pre_post_plugins_constructor_args_removed():
    """pre_plugins and post_plugins constructor args must be rejected (removed)."""
    with pytest.raises(TypeError, match="pre_plugins|unexpected keyword"):
        NodeExecutionRuntime(provider_executor=None, pre_plugins=[object()])

    with pytest.raises(TypeError, match="post_plugins|unexpected keyword"):
        NodeExecutionRuntime(provider_executor=None, post_plugins=[object()])
