from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.prompt_registry import PromptRegistry
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry


class RecordingProvider:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {
            "output": f"provider:{request.prompt}",
            "trace": {"provider": "recording"},
        }


def _make_runtime(tmp_path: Path, *, registry_root: Path):
    provider = RecordingProvider()
    provider_registry = ProviderRegistry()
    provider_registry.register("fake", provider)
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(provider_registry),
        prompt_registry=PromptRegistry(root=str(registry_root)),
        observability_file=str(tmp_path / "obs.jsonl"),
    )
    return runtime, provider


def test_step190_runtime_uses_prompt_registry_for_explicit_prompt_version(tmp_path: Path):
    prompt_dir = tmp_path / "registry" / "prompts" / "qa_prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"qa_prompt/v1","version":"v1","inputs_schema":{"question":"str"}}-->\n'
        'Question: {question}?',
        encoding="utf-8",
    )

    runtime, provider = _make_runtime(tmp_path, registry_root=tmp_path / "registry" / "prompts")

    config = {
        "config_id": "ec_prompt_registry",
        "prompt_ref": "qa_prompt",
        "prompt_version": "v1",
        "prompt_inputs": {"question": "input.question"},
        "provider_ref": "fake",
        "runtime_config": {"return_raw_output": True},
    }

    result = runtime.execute(config, {"question": "nexa"})

    assert result.output == "provider:Question: nexa?"
    assert provider.requests[0].prompt == "Question: nexa?"
    assert "prompt_render" in result.trace.events


def test_step190_runtime_blocks_when_prompt_spec_render_fails(tmp_path: Path):
    prompt_dir = tmp_path / "registry" / "prompts" / "qa_prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"qa_prompt/v1","version":"v1","inputs_schema":{"question":"str"}}-->\n'
        'Question: {question}?',
        encoding="utf-8",
    )

    runtime, _provider = _make_runtime(tmp_path, registry_root=tmp_path / "registry" / "prompts")

    config = {
        "config_id": "ec_prompt_registry_error",
        "prompt_ref": "qa_prompt",
        "prompt_version": "v1",
        "prompt_inputs": {"question": "input.question"},
        "provider_ref": "fake",
        "runtime_config": {"return_raw_output": True},
    }

    with pytest.raises(ValueError, match="prompt render failed"):
        runtime.execute(config, {"wrong_key": "nexa"})
