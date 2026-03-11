from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.platform.plugin_result import PluginResult


class RecordingProvider:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {
            "output": f"provider:{request.prompt}",
            "trace": {"provider": "recording"},
        }


def test_step135_runtime_is_graph_only_and_ignores_pre_post_plugin_stages(tmp_path):
    provider = RecordingProvider()
    registry = ProviderRegistry()
    registry.register("openai", provider)

    called = []

    class LegacyPre:
        def run(self, **kwargs):
            called.append("pre")
            return PluginResult(output={"result": "legacy-pre"})

    class LegacyPost:
        def run(self, **kwargs):
            called.append("post")
            return PluginResult(output={"result": "legacy-post"})

    def search(query):
        called.append("graph")
        return PluginResult(output={"result": f"search:{query}"})

    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        pre_plugins=[LegacyPre()],
        post_plugins=[LegacyPost()],
        plugin_registry={"search": search},
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_graph_only",
        "plugins": [
            {
                "plugin_id": "search",
                "inputs": {"query": "input.query"},
                "output_fields": ["result"],
            }
        ],
    }

    result = runtime.execute(config, {"query": "nexa"})

    assert result.output == "search:nexa"

    # legacy pre/post plugin objects must not be executed
    assert called == ["graph"]

    # lifecycle trace markers are preserved for observability compatibility
    assert "pre_plugins" in result.trace.events
    assert "post_plugins" in result.trace.events

    # actual graph execution trace must still exist
    assert any(event.startswith("plugin_execute:search") for event in result.trace.events)
    assert any(event.startswith("wave:") for event in result.trace.events)

    # noop compatibility markers remain because pre/post stages are not executed
    assert "noop_pre_plugin" in result.trace.plugin_trace["pre"]