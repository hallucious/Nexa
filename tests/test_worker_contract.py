from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from src.platform.worker import WorkerResult, wrap_text_provider
from src.providers.provider_contract import make_success, make_failure, ProviderResult


class _FakeProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = bool(fail)

    def fingerprint(self) -> str:
        return "fp-fake-v1"


    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any], Optional[BaseException]]:
        if self.fail:
            return "", {}, RuntimeError("boom")
        return f"echo:{prompt}", {"ok": True, "temperature": temperature}, None



class _FakeProviderV2:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = bool(fail)

    def fingerprint(self) -> str:
        return "fp-fake-v2"


    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
    ) -> ProviderResult:
        if self.fail:
            return make_failure(error="boom", raw={}, reason_code="AI.provider_error", latency_ms=12)
        return make_success(text=f"echo:{prompt}", raw={"ok": True, "temperature": temperature}, latency_ms=12)


def test_worker_adapter_success():
    worker = wrap_text_provider(name="gpt", provider=_FakeProvider(fail=False))
    result = worker.generate_text(prompt="hi", temperature=0.2, max_output_tokens=10)

    assert isinstance(result, WorkerResult)
    assert result.success is True
    assert result.error is None
    assert result.text == "echo:hi"
    assert result.raw.get("ok") is True
    assert result.worker_name == "gpt"
    assert isinstance(result.latency_ms, int)


def test_worker_adapter_failure_normalizes_error():
    worker = wrap_text_provider(name="gpt", provider=_FakeProvider(fail=True))
    result = worker.generate_text(prompt="hi")

    assert result.success is False
    assert isinstance(result.error, str) and result.error.strip() != ""
    assert result.text == ""


def test_worker_adapter_accepts_provider_result_envelope():
    worker = wrap_text_provider(name="gpt", provider=_FakeProviderV2(fail=False))
    result = worker.generate_text(prompt="hi", temperature=0.2, max_output_tokens=10)
    assert result.success is True
    assert result.error is None
    assert result.text == "echo:hi"
    assert result.raw.get("ok") is True


def test_worker_adapter_failure_from_provider_result_envelope():
    worker = wrap_text_provider(name="gpt", provider=_FakeProviderV2(fail=True))
    result = worker.generate_text(prompt="hi")
    assert result.success is False
    assert isinstance(result.error, str) and result.error.strip() != ""
    assert result.text == ""
