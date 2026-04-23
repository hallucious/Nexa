from pathlib import Path

from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.prompt_registry import PromptRegistry
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class DummyProvider:
    def execute(self, request):
        return {"output": f"echo:{request.prompt}", "trace": {"provider": "dummy"}}


def _make_prompt_registry(tmp_path: Path, prompt_id: str) -> PromptRegistry:
    """Create a PromptRegistry backed by a stub prompt spec file in tmp_path."""
    prompt_dir = tmp_path / "prompts" / prompt_id
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"' + prompt_id + '/v1","version":"v1","inputs_schema":{}}-->\n'
        "stub prompt",
        encoding="utf-8",
    )
    return PromptRegistry(root=str(tmp_path / "prompts"))


def test_step106_node_trace_observability_contract(tmp_path):
    registry = ProviderRegistry()
    registry.register("dummy", DummyProvider())
    prompt_registry = _make_prompt_registry(tmp_path, "basic")
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        prompt_registry=prompt_registry,
        observability_file=str(tmp_path / "obs.jsonl"),
    )

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
