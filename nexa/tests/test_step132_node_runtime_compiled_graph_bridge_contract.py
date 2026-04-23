from pathlib import Path

from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.prompt_registry import PromptRegistry
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


def _stub_prompt_registry(tmp_path: Path, prompt_id: str, template: str = "stub prompt") -> PromptRegistry:
    """Create a PromptRegistry backed by a minimal stub prompt spec."""
    prompt_dir = tmp_path / "prompts" / prompt_id
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"' + prompt_id + '/v1","version":"v1","inputs_schema":{}}-->\n'
        + template,
        encoding="utf-8",
    )
    return PromptRegistry(root=str(tmp_path / "prompts"))


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
    """Verify that the compiled graph correctly routes prompt → provider output.

    Migrated from Path B (legacy symbolic prompt_ref) to Path A (registry-backed prompt spec).
    The core contract being tested is that compiled graph routing works correctly:
    a rendered prompt is passed to the provider and surfaced via output_mapping.
    """
    provider = RecordingProvider()
    provider_registry = ProviderRegistry()
    provider_registry.register("fake", provider)
    prompt_registry = _stub_prompt_registry(tmp_path, "prompt.basic", template="basic stub prompt")
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(provider_registry),
        prompt_registry=prompt_registry,
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_existing",
        "prompt_ref": "prompt.basic",
        "prompt_version": "v1",
        "provider_ref": "fake",
        "output_mapping": {"answer": "provider.fake.output"},
    }

    result = runtime.execute(config, {"question": "test"})

    assert result.output["answer"] == "provider:basic stub prompt"
    assert provider.requests[0].prompt == "basic stub prompt"
    assert result.trace.provider_trace["provider"] == "recording"