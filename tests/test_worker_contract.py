from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from src.platform.worker import WorkerResult, wrap_text_provider


class _FakeProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = bool(fail)

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
