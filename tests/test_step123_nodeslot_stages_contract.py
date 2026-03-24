"""
test_step123 — Node execution stages contract.
pre_plugins/post_plugins are not accepted in execution configs.
"""
import pytest
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class FakeProvider:
    def execute(self, request):
        return {"answer": "ok", "prompt": request.prompt}


def test_step123_stages_basic(tmp_path):
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider())
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
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
