from __future__ import annotations

from pathlib import Path

import pytest

from src.providers.codex_provider import CodexProvider
from src.providers.gpt_provider import GPTProvider
from src.providers.openai_provider import OpenAIProvider
from src.providers.env_diagnostics import publish_dotenv_status


@pytest.mark.parametrize("provider_cls", [OpenAIProvider, GPTProvider, CodexProvider])
def test_provider_from_env_uses_existing_process_env(monkeypatch, tmp_path, provider_cls):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("NEXA_DOTENV_INSTALLED", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_PATH", raising=False)

    provider = provider_cls.from_env()

    assert provider.api_key == "sk-test"


@pytest.mark.parametrize("provider_cls", [OpenAIProvider, GPTProvider, CodexProvider])
def test_provider_from_env_reports_missing_dotenv_file(monkeypatch, tmp_path, provider_cls):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_INSTALLED", raising=False)
    monkeypatch.delenv("NEXA_DOTENV_PATH", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        provider_cls.from_env()

    message = str(exc_info.value)
    assert "No .env file was found" in message
    assert "OPENAI_API_KEY=your_key_here" in message


@pytest.mark.parametrize("provider_cls", [OpenAIProvider, GPTProvider, CodexProvider])
def test_provider_from_env_reports_missing_python_dotenv(monkeypatch, tmp_path, provider_cls):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    publish_dotenv_status(installed=False, loaded_path=str(dotenv_path))

    with pytest.raises(RuntimeError) as exc_info:
        provider_cls.from_env()

    message = str(exc_info.value)
    assert "python-dotenv is not installed" in message
    assert str(dotenv_path) in message


@pytest.mark.parametrize("provider_cls", [OpenAIProvider, GPTProvider, CodexProvider])
def test_provider_from_env_reports_missing_key_in_dotenv(monkeypatch, tmp_path, provider_cls):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("OTHER_KEY=value\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    publish_dotenv_status(installed=True, loaded_path=str(dotenv_path))

    with pytest.raises(RuntimeError) as exc_info:
        provider_cls.from_env()

    message = str(exc_info.value)
    assert "OPENAI_API_KEY is missing or empty" in message
    assert str(dotenv_path) in message
