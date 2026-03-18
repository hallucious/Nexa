from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor
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


def test_step132_runtime_executes_compiled_graph_with_reverse_plugin_to_provider_dependency(tmp_path):
    provider = RecordingProvider()
    registry = ProviderRegistry()
    registry.register("openai", provider)

    def search_plugin(query):
        return PluginResult(output={"result": f"search:{query}"})

    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        plugin_registry={"search": search_plugin},
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_reverse_dep",
        "provider": {
            "provider_id": "openai",
            "inputs": {"text": "plugin.search.result"},
        },
        "plugins": [
            {
                "plugin_id": "search",
                "inputs": {"query": "input.query"},
                "output_fields": ["result"],
            }
        ],
        "output_mapping": {
            "answer": "provider.openai.output",
        },
    }

    result = runtime.execute(config, {"query": "nexa"})

    assert result.output == {"answer": "provider:search:nexa"}
    assert provider.requests[0].prompt == "search:nexa"
    assert provider.requests[0].context["plugin.search.result"] == "search:nexa"


def test_step132_runtime_keeps_existing_prompt_provider_contract_under_compiled_graph(tmp_path):
    provider = RecordingProvider()
    registry = ProviderRegistry()
    registry.register("fake", provider)
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_existing",
        "prompt_ref": "prompt.basic",
        "provider_ref": "fake",
        "output_mapping": {"answer": "provider.fake.output"},
    }

    result = runtime.execute(config, {"question": "test"})

    assert result.output["answer"].startswith("provider:prompt.basic:")
    assert result.trace.provider_trace["provider"] == "recording"