"""
test_step123 — Node execution stages contract.
pre_plugins/post_plugins are not accepted in execution configs.
"""
import pytest
from pathlib import Path
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.prompt_registry import PromptRegistry
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class FakeProvider:
    def execute(self, request):
        return {"answer": "ok", "prompt": request.prompt}


def _stub_registry(tmp_path: Path, prompt_id: str) -> PromptRegistry:
    """Create a PromptRegistry backed by a minimal stub prompt spec."""
    prompt_dir = tmp_path / "prompts" / prompt_id
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"' + prompt_id + '/v1","version":"v1","inputs_schema":{}}-->\n'
        "stub prompt",
        encoding="utf-8",
    )
    return PromptRegistry(root=str(tmp_path / "prompts"))


def test_step123_stages_basic(tmp_path):
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider())
    prompt_registry = _stub_registry(tmp_path, "prompt.basic")
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        prompt_registry=prompt_registry,
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_test",
        "prompt_ref": "prompt.basic",
        "provider_ref": "fake",
        "validation_rules": [],
        "output_mapping": {"answer": "answer"},
    }

    result = runtime.execute(config, {"question": "test"})
    assert result.output["answer"] == "ok"


def test_step123_pre_plugins_rejected_in_config():
    """pre_plugins is no longer a valid execution config field."""
    from src.platform.execution_config_registry import ExecutionConfigFormatError, ExecutionConfigModel
    with pytest.raises(ExecutionConfigFormatError, match="pre_plugins"):
        ExecutionConfigModel.from_dict({
            "config_id": "bad", "version": "1.0.0", "pre_plugins": ["p1"],
        })


def test_step123_post_plugins_rejected_in_config():
    """post_plugins is no longer a valid execution config field."""
    from src.platform.execution_config_registry import ExecutionConfigFormatError, ExecutionConfigModel
    with pytest.raises(ExecutionConfigFormatError, match="post_plugins"):
        ExecutionConfigModel.from_dict({
            "config_id": "bad", "version": "1.0.0", "post_plugins": ["p1"],
        })
