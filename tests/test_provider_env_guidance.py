from __future__ import annotations

from pathlib import Path

import pytest

from src.providers.claude_provider import ClaudeProvider
from src.providers.codex_provider import CodexProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.gpt_provider import GPTProvider
from src.providers.openai_provider import OpenAIProvider
from src.providers.perplexity_provider import PerplexityProvider
from src.providers.env_diagnostics import publish_dotenv_status


_PROVIDER_CASES = [
    (OpenAIProvider, "OPENAI_API_KEY", (), "OPENAI_API_KEY"),
    (GPTProvider, "OPENAI_API_KEY", (), "OPENAI_API_KEY"),
    (CodexProvider, "OPENAI_API_KEY", (), "OPENAI_API_KEY"),
    (ClaudeProvider, "ANTHROPIC_API_KEY", (), "ANTHROPIC_API_KEY"),
    (GeminiProvider, "GEMINI_API_KEY", (), "GEMINI_API_KEY"),
    (PerplexityProvider, "PERPLEXITY_API_KEY", ("PPLX_API_KEY",), "PERPLEXITY_API_KEY"),
]


@pytest.mark.parametrize(
    ("provider_cls", "env_var_name", "aliases", "message_var_name"),
    _PROVIDER_CASES,
)
def test_provider_from_env_uses_existing_process_env(monkeypatch, tmp_path, provider_cls, env_var_name, aliases, message_var_name):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(env_var_name, "sk-test")
    for alias in aliases:
        monkeypatch.delenv(alias, raising=False)
    monkeypatch.delenv("NEXA_DOTENV_INSTALLED", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_PATH", raising=False)

    provider = provider_cls.from_env()

    assert provider.api_key == "sk-test"


@pytest.mark.parametrize(
    ("provider_cls", "env_var_name", "aliases", "message_var_name"),
    _PROVIDER_CASES,
)
def test_provider_from_env_reports_missing_dotenv_file(monkeypatch, tmp_path, provider_cls, env_var_name, aliases, message_var_name):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(env_var_name, raising=False)
    for alias in aliases:
        monkeypatch.delenv(alias, raising=False)
    monkeypatch.delenv("NEXA_DOTENV_INSTALLED", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_PATH", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        provider_cls.from_env()

    message = str(exc_info.value)
    assert "No .env file was found" in message
    assert f"{message_var_name}=your_key_here" in message


@pytest.mark.parametrize(
    ("provider_cls", "env_var_name", "aliases", "message_var_name"),
    _PROVIDER_CASES,
)
def test_provider_from_env_reports_missing_python_dotenv(monkeypatch, tmp_path, provider_cls, env_var_name, aliases, message_var_name):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(f"{message_var_name}=\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(env_var_name, raising=False)
    for alias in aliases:
        monkeypatch.delenv(alias, raising=False)
    publish_dotenv_status(installed=False, loaded_path=str(dotenv_path))

    with pytest.raises(RuntimeError) as exc_info:
        provider_cls.from_env()

    message = str(exc_info.value)
    assert "python-dotenv is not installed" in message
    assert str(dotenv_path) in message


@pytest.mark.parametrize(
    ("provider_cls", "env_var_name", "aliases", "message_var_name"),
    _PROVIDER_CASES,
)
def test_provider_from_env_reports_missing_key_in_dotenv(monkeypatch, tmp_path, provider_cls, env_var_name, aliases, message_var_name):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("OTHER_KEY=value\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(env_var_name, raising=False)
    for alias in aliases:
        monkeypatch.delenv(alias, raising=False)
    publish_dotenv_status(installed=True, loaded_path=str(dotenv_path))

    with pytest.raises(RuntimeError) as exc_info:
        provider_cls.from_env()

    message = str(exc_info.value)
    assert f"{message_var_name} is missing or empty" in message
    assert str(dotenv_path) in message


def test_perplexity_provider_accepts_legacy_pplx_env_var(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.setenv("PPLX_API_KEY", "pplx-test")
    monkeypatch.delenv("NEXA_DOTENV_INSTALLED", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_PATH", raising=False)

    provider = PerplexityProvider.from_env()

    assert provider.api_key == "pplx-test"
