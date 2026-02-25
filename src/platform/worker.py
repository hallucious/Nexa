from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

from .safe_exec import safe_call


@dataclass
class WorkerResult:
    success: bool
    text: str
    raw: Dict[str, Any]
    error: Optional[str]
    latency_ms: int
    worker_name: str


class TextWorker(Protocol):
    name: str

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> WorkerResult:
        ...


class ProviderTextWorker:
    """Adapter that wraps an existing provider with a generate_text(...) -> (text, raw, err) signature.

    Step37: add soft timeout + crash containment via safe_call().
    """

    def __init__(self, *, name: str, provider: Any) -> None:
        self.name = str(name)
        self._provider = provider

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> WorkerResult:
        def _call_provider() -> Tuple[Any, Any, Any]:
            # Provider contract (existing codebase):
            #   generate_text(prompt=..., temperature=..., max_output_tokens=..., instructions=...) -> (text, raw, err)
            return self._provider.generate_text(
                prompt=prompt,
                temperature=float(temperature),
                max_output_tokens=int(max_output_tokens),
                instructions=instructions,
            )

        res = safe_call(fn=_call_provider, timeout_ms=timeout_ms)

        if res.ok:
            try:
                text, raw, err = res.value  # type: ignore[misc]
                success = err is None
                error = None if err is None else f"{type(err).__name__}: {err}"
                if not isinstance(raw, dict):
                    raw = {}
                if not isinstance(text, str):
                    text = str(text)
            except Exception as e:  # noqa: BLE001
                text = ""
                raw = {}
                success = False
                error = f"{type(e).__name__}: {e}"
        else:
            text = ""
            raw = {}
            success = False
            error = res.error

        return WorkerResult(
            success=success,
            text=text,
            raw=raw,
            error=error,
            latency_ms=res.latency_ms,
            worker_name=self.name,
        )


def wrap_text_provider(*, name: str, provider: Any) -> TextWorker:
    """Convenience helper to create a ProviderTextWorker."""
    return ProviderTextWorker(name=name, provider=provider)
