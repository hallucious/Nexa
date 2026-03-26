"""
test_step199 — Prompt path convergence contract.

This test file locks the boundary between:

A. Modern prompt runtime path
   - NodeExecutionRuntime + src/platform/prompt_registry.py
   - PromptRegistry resolves from registry/prompts/{id}/vX.md
   - Hard failure on any resolution or render error

B. Bounded legacy compatibility path
   - prompt_ref without prompt_version + no registry entry
   - Falls back to deterministic "{prompt_ref}:{context}" placeholder
   - NOT a silent success — the fallback is explicit and bounded

Rules:
- Modern path (prompt_version explicit) MUST fail hard if the prompt is not found.
- Modern path (prompt registered) MUST succeed and render correctly.
- Legacy fallback MUST only trigger when prompt_version is absent AND registry has no entry.
- Legacy fallback output is deterministic (same inputs → same output).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.prompt_registry import PromptRegistry
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry


class EchoProvider:
    def __init__(self):
        self.last_prompt = None

    def execute(self, request):
        self.last_prompt = request.prompt
        return {
            "output": f"echo:{request.prompt}",
            "trace": {"provider": "echo"},
        }


def _make_runtime(tmp_path: Path, *, prompt_registry=None) -> tuple:
    provider = EchoProvider()
    provider_registry = ProviderRegistry()
    provider_registry.register("echo", provider)
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(provider_registry),
        prompt_registry=prompt_registry,
        observability_file=str(tmp_path / "obs.jsonl"),
    )
    return runtime, provider


# ──────────────────────────────────────────────
# A. Modern path: registry-backed prompt
# ──────────────────────────────────────────────

def test_step199_modern_path_explicit_version_resolves_and_renders(tmp_path):
    """Modern path: prompt_ref + prompt_version + registry entry → renders correctly."""
    prompt_dir = tmp_path / "prompts" / "greet"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"greet/v1","version":"v1","inputs_schema":{"name":"str"}}-->\n'
        "Hello, {name}!",
        encoding="utf-8",
    )
    prompt_registry = PromptRegistry(root=str(tmp_path / "prompts"))
    runtime, provider = _make_runtime(tmp_path, prompt_registry=prompt_registry)

    config = {
        "config_id": "ec_modern",
        "prompt_ref": "greet",
        "prompt_version": "v1",
        "prompt_inputs": {"name": "input.name"},
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    result = runtime.execute(config, {"name": "Nexa"})

    assert provider.last_prompt == "Hello, Nexa!"
    assert "prompt_render" in result.trace.events


def test_step199_modern_path_latest_version_resolves(tmp_path):
    """Modern path: prompt_ref without prompt_version → resolves latest."""
    prompt_dir = tmp_path / "prompts" / "greet"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"greet/v1","version":"v1","inputs_schema":{}}-->\n'
        "stub v1",
        encoding="utf-8",
    )
    (prompt_dir / "v2.md").write_text(
        '<!--PROMPT_SPEC: {"id":"greet/v2","version":"v2","inputs_schema":{}}-->\n'
        "stub v2",
        encoding="utf-8",
    )
    prompt_registry = PromptRegistry(root=str(tmp_path / "prompts"))
    runtime, provider = _make_runtime(tmp_path, prompt_registry=prompt_registry)

    config = {
        "config_id": "ec_latest",
        "prompt_ref": "greet",
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    result = runtime.execute(config, {})
    assert provider.last_prompt == "stub v2"


# ──────────────────────────────────────────────
# B. Modern path: hard failure cases
# ──────────────────────────────────────────────

def test_step199_modern_path_explicit_version_missing_fails_hard(tmp_path):
    """When prompt_version is explicit but the file is missing, MUST raise ValueError."""
    prompt_registry = PromptRegistry(root=str(tmp_path / "prompts"))
    runtime, _provider = _make_runtime(tmp_path, prompt_registry=prompt_registry)

    config = {
        "config_id": "ec_hard_fail",
        "prompt_ref": "nonexistent",
        "prompt_version": "v1",
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    with pytest.raises(ValueError, match="prompt resolution failed"):
        runtime.execute(config, {})


def test_step199_modern_path_render_failure_raises(tmp_path):
    """When registry resolves but render fails (missing required input), MUST raise ValueError."""
    prompt_dir = tmp_path / "prompts" / "strict"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "v1.md").write_text(
        '<!--PROMPT_SPEC: {"id":"strict/v1","version":"v1","inputs_schema":{"required_key":"str"}}-->\n'
        "input: {required_key}",
        encoding="utf-8",
    )
    prompt_registry = PromptRegistry(root=str(tmp_path / "prompts"))
    runtime, _provider = _make_runtime(tmp_path, prompt_registry=prompt_registry)

    config = {
        "config_id": "ec_render_fail",
        "prompt_ref": "strict",
        "prompt_version": "v1",
        "prompt_inputs": {"required_key": "input.missing"},
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    with pytest.raises(ValueError, match="prompt render failed"):
        runtime.execute(config, {})


# ──────────────────────────────────────────────
# C. Legacy fallback path: bounded and deterministic
# ──────────────────────────────────────────────

def test_step199_legacy_fallback_triggers_only_when_no_version_and_no_registry_entry(tmp_path):
    """Legacy fallback MUST only trigger when prompt_version is absent AND no registry entry."""
    # Default PromptRegistry points to non-existent dir → all lookups fail
    runtime, provider = _make_runtime(tmp_path)

    config = {
        "config_id": "ec_legacy",
        "prompt_ref": "symbolic.prompt",
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    result = runtime.execute(config, {"key": "val"})
    # Fallback must render something deterministic (the placeholder pattern)
    assert provider.last_prompt.startswith("symbolic.prompt:")
    assert "prompt_render" in result.trace.events


def test_step199_legacy_fallback_is_deterministic(tmp_path):
    """Legacy fallback output must be identical for identical inputs."""
    runtime1, provider1 = _make_runtime(tmp_path)
    runtime2, provider2 = _make_runtime(tmp_path)

    config = {
        "config_id": "ec_determ",
        "prompt_ref": "determ.prompt",
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    state = {"key": "value"}

    runtime1.execute(config, dict(state))
    runtime2.execute(config, dict(state))

    assert provider1.last_prompt == provider2.last_prompt


def test_step199_legacy_fallback_does_not_trigger_when_version_is_set(tmp_path):
    """Explicit prompt_version with no registry entry MUST fail hard, not fall back silently."""
    runtime, _provider = _make_runtime(tmp_path)

    config = {
        "config_id": "ec_no_silent",
        "prompt_ref": "symbolic.prompt",
        "prompt_version": "v1",
        "provider_ref": "echo",
        "runtime_config": {"return_raw_output": True},
    }
    with pytest.raises(ValueError, match="prompt resolution failed"):
        runtime.execute(config, {})
