from __future__ import annotations

import types

from src.contracts.provider_contract import ProviderRequest
from src.contracts.savefile_format import (
    CircuitSpec,
    ResourcesSpec,
    Savefile,
    SavefileMeta,
    StateSpec,
    UISpec,
)
from src.contracts.savefile_provider_builder import build_provider_registry_from_savefile
from src.platform.provider_executor import GenerateTextProviderBridge


class _TupleSuccessProvider:
    def generate_text(self, *, prompt: str, temperature: float = 0.0, max_output_tokens: int = 1024):
        return (f"ok:{prompt}", {"source": "tuple"}, None)


class _TupleFailureProvider:
    def generate_text(self, *, prompt: str, temperature: float = 0.0, max_output_tokens: int = 1024):
        return ("", {"source": "tuple"}, RuntimeError("boom"))


def _minimal_savefile(*, provider_type: str, model: str = "model-x") -> Savefile:
    return Savefile(
        meta=SavefileMeta(name="demo", version="1.0.0"),
        circuit=CircuitSpec(entry="n1", nodes=[]),
        resources=ResourcesSpec(
            providers={
                "p1": types.SimpleNamespace(
                    type=provider_type,
                    model=model,
                    config={"timeout_sec": 33},
                )
            }
        ),
        state=StateSpec(),
        ui=UISpec(),
    )


def test_step197_shared_generate_text_bridge_success():
    bridge = GenerateTextProviderBridge(_TupleSuccessProvider(), provider_name="fake")
    request = ProviderRequest(provider_id="fake", prompt="hello", context={}, options={}, metadata={})

    result = bridge.execute(request)

    assert result.error is None
    assert result.output == "ok:hello"
    assert result.trace["provider"] == "fake"
    assert result.structured == {"source": "tuple"}


def test_step197_shared_generate_text_bridge_failure():
    bridge = GenerateTextProviderBridge(_TupleFailureProvider(), provider_name="fake")
    request = ProviderRequest(provider_id="fake", prompt="hello", context={}, options={}, metadata={})

    result = bridge.execute(request)

    assert result.error is not None
    assert result.error.message == "boom"
    assert result.trace["provider"] == "fake"


def test_step197_savefile_builder_uses_claude_provider_module(monkeypatch):
    class _FakeClaudeProvider:
        DEFAULT_MODEL = "claude-test"

        def __init__(self, api_key: str, *, model: str, timeout_sec: int):
            self.api_key = api_key
            self.model = model
            self.timeout_sec = timeout_sec

        def generate_text(self, *, prompt: str, temperature: float = 0.0, max_output_tokens: int = 1024):
            return (f"claude:{prompt}", {"model": self.model, "timeout_sec": self.timeout_sec}, None)

    fake_module = types.SimpleNamespace(ClaudeProvider=_FakeClaudeProvider)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(__import__("sys").modules, "src.providers.claude_provider", fake_module)

    registry = build_provider_registry_from_savefile(_minimal_savefile(provider_type="anthropic", model="claude-sonnet-test"))
    provider = registry.resolve("p1")
    request = ProviderRequest(provider_id="p1", prompt="hi", context={}, options={}, metadata={})

    result = provider.execute(request)

    assert result.error is None
    assert result.output == "claude:hi"
    assert result.trace["provider"] == "anthropic"
    assert result.structured == {"model": "claude-sonnet-test", "timeout_sec": 33}
