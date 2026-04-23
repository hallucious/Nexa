from src.engine.compiled_resource_graph import compile_execution_config_to_graph
from src.engine.final_output_resolver import resolve_final_output
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


def test_step134_resolver_selects_plugin_result_before_provider_output():
    graph = compile_execution_config_to_graph(
        {
            "prompt": {
                "prompt_id": "main",
                "inputs": {"question": "input.question"},
            },
            "provider": {
                "provider_id": "openai",
            },
            "plugins": [
                {
                    "plugin_id": "search",
                    "inputs": {"query": "input.question"},
                    "output_fields": ["result", "metadata"],
                }
            ],
        }
    )

    flat_context = {
        "input.question": "nexa",
        "prompt.main.rendered": "prompt:nexa",
        "provider.openai.output": "provider:prompt:nexa",
        "plugin.search.result": "search:nexa",
        "plugin.search.metadata": {"hits": 1},
    }

    resolved = resolve_final_output(graph, flat_context)

    assert resolved.value == "search:nexa"
    assert resolved.source_key == "plugin.search.result"
    assert resolved.candidates == [
        "plugin.search.result",
        "plugin.search.metadata",
        "provider.openai.output",
    ]


def test_step134_runtime_uses_final_output_resolver_when_output_mapping_missing(tmp_path):
    provider = RecordingProvider()
    registry = ProviderRegistry()
    registry.register("openai", provider)

    def search_plugin(query):
        return PluginResult(
            output={
                "result": f"search:{query}",
                "metadata": {"hits": 1},
            }
        )

    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        plugin_registry={"search": search_plugin},
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_final_output",
        "prompt": {
            "prompt_id": "main",
            "inputs": {"question": "input.question"},
        },
        "provider": {
            "provider_id": "openai",
        },
        "plugins": [
            {
                "plugin_id": "search",
                "inputs": {"query": "input.question"},
                "output_fields": ["result", "metadata"],
            }
        ],
    }

    result = runtime.execute(config, {"question": "nexa"})

    assert result.output == "search:nexa"
    assert "final_output:plugin.search.result" in result.trace.events


def test_step134_explicit_output_mapping_still_overrides_automatic_resolution(tmp_path):
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
        "config_id": "ec_mapping_override",
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
    assert "final_output:explicit_mapping" in result.trace.events