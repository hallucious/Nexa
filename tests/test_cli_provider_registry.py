from __future__ import annotations

import types

from src.cli.nexa_cli import _GenerateTextProviderAdapter, _maybe_register_real_providers
from src.platform.provider_registry import ProviderRegistry
from src.contracts.provider_contract import ProviderRequest


class _SuccessProvider:
    def generate_text(self, *, prompt: str, temperature: float = 0.0, max_output_tokens: int = 1024):
        return (f"OK:{prompt}", {"provider": "fake"}, None)


class _FailureProvider:
    def generate_text(self, *, prompt: str, temperature: float = 0.0, max_output_tokens: int = 1024):
        return ("", {"provider": "fake"}, RuntimeError("boom"))


def test_generate_text_provider_adapter_success():
    adapter = _GenerateTextProviderAdapter(_SuccessProvider(), "fake")
    request = ProviderRequest(provider_id="fake", prompt="hello", context={}, options={}, metadata={})

    result = adapter.execute(request)

    assert result.error is None
    assert result.output == "OK:hello"
    assert result.trace["provider"] == "fake"


def test_generate_text_provider_adapter_failure():
    adapter = _GenerateTextProviderAdapter(_FailureProvider(), "fake")
    request = ProviderRequest(provider_id="fake", prompt="hello", context={}, options={}, metadata={})

    result = adapter.execute(request)

    assert result.error is not None
    assert result.error.message == "boom"


def test_registers_openai_aliases(monkeypatch):
    class _FakeGPTProvider:
        @classmethod
        def from_env(cls):
            return _SuccessProvider()

    fake_module = types.SimpleNamespace(GPTProvider=_FakeGPTProvider)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(__import__("sys").modules, "src.providers.gpt_provider", fake_module)

    registry = ProviderRegistry()
    _maybe_register_real_providers(registry)

    assert "openai" in registry.list_providers()
    assert "gpt" in registry.list_providers()
    assert "ai" in registry.list_providers()
