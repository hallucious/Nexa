from __future__ import annotations

import json

import pytest
import src.providers.claude_provider as claude_provider_module

from src.designer.semantic_interpreter import LLMBackedStructuredSemanticInterpreter, LegacyRuleBasedSemanticInterpreter
from src.designer.semantic_interpreter_factory import build_designer_semantic_interpreter
from src.providers.provider_contract import ProviderMetrics, ProviderResult


class _GenerateTextProvider:
    def __init__(self, *, text: str | None = None):
        self.text = text or json.dumps({"category": "MODIFY_CIRCUIT", "action_candidates": []})

    def generate_text(self, **kwargs):
        return ProviderResult(
            success=True,
            text=self.text,
            raw={},
            error=None,
            reason_code=None,
            metrics=ProviderMetrics(latency_ms=8),
        )



def test_build_designer_semantic_interpreter_returns_legacy_by_default() -> None:
    interpreter = build_designer_semantic_interpreter()
    assert isinstance(interpreter, LegacyRuleBasedSemanticInterpreter)



def test_build_designer_semantic_interpreter_builds_llm_path_from_preset() -> None:
    interpreter = build_designer_semantic_interpreter(
        semantic_backend_preset="anthropic",
        semantic_backend_preset_providers={"claude": _GenerateTextProvider()},
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )
    assert isinstance(interpreter, LLMBackedStructuredSemanticInterpreter)
    assert interpreter.backend.provider_name == "designer.semantic.claude"



def test_build_designer_semantic_interpreter_requires_backend_when_requested() -> None:
    with pytest.raises(ValueError, match="semantic_backend is required"):
        build_designer_semantic_interpreter(
            use_llm_semantic_interpreter=True,
            llm_backend_required=True,
        )


def test_build_designer_semantic_interpreter_builds_llm_path_from_env_preset(monkeypatch) -> None:
    provider = _GenerateTextProvider()

    def _fake_from_env(cls):
        return provider

    monkeypatch.setattr(claude_provider_module.ClaudeProvider, "from_env", classmethod(_fake_from_env))
    interpreter = build_designer_semantic_interpreter(
        semantic_backend_preset="claude",
        semantic_backend_preset_use_env=True,
        use_llm_semantic_interpreter=True,
        llm_backend_required=True,
    )
    assert isinstance(interpreter, LLMBackedStructuredSemanticInterpreter)
    assert interpreter.backend.provider is provider
