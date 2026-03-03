from __future__ import annotations

import json
from typing import Any, Dict
import urllib.request


class _DummyResp:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._bytes = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._bytes

    def __enter__(self) -> "_DummyResp":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_step95_universal_provider_delegates_openai_responses(monkeypatch):
    from src.providers.gpt_provider import GPTProvider

    captured = {}

    def fake_urlopen(req: urllib.request.Request, timeout: int = 0):  # type: ignore[override]
        body = req.data.decode("utf-8") if req.data else ""
        captured["url"] = req.full_url
        captured["body"] = json.loads(body) if body else {}
        return _DummyResp(
            {
                "output": [
                    {"content": [{"type": "output_text", "text": "hello"}]}
                ],
                "usage": {"output_tokens": 3},
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    p = GPTProvider(api_key="k", model="m1", timeout_sec=1)
    res = p.generate_text(prompt="hi", temperature=0.0, max_output_tokens=16)
    assert res.success is True
    assert res.text == "hello"
    assert isinstance(res.raw, dict)
    assert captured["url"].endswith("/v1/responses")
    assert captured["body"]["model"] == "m1"


def test_step95_universal_provider_delegates_openai_chat_completions(monkeypatch):
    from src.providers.perplexity_provider import PerplexityProvider

    def fake_urlopen(req: urllib.request.Request, timeout: int = 0):  # type: ignore[override]
        return _DummyResp(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}}
                ],
                "usage": {"completion_tokens": 2},
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    p = PerplexityProvider(api_key="k", model="sonar", timeout_sec=1)
    res = p.generate_text(prompt="hi", temperature=0.0, max_output_tokens=16)
    assert res.success is True
    assert res.text == "ok"
    assert isinstance(res.raw, dict)


def test_step95_universal_provider_delegates_anthropic_messages(monkeypatch):
    from src.providers.claude_provider import ClaudeProvider

    def fake_urlopen(req: urllib.request.Request, timeout: int = 0):  # type: ignore[override]
        return _DummyResp(
            {
                "content": [{"type": "text", "text": "yo"}],
                "usage": {"output_tokens": 1},
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    p = ClaudeProvider(api_key="k", model="m1", timeout_sec=1)
    res = p.generate_text(prompt="hi", temperature=0.0, max_output_tokens=16)
    assert res.success is True
    assert res.text == "yo"
    assert isinstance(res.raw, dict)
