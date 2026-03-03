from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple, Union

from .safe_exec import safe_call
from src.providers.provider_contract import ProviderResult


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
    """Adapter wrapping a provider with generate_text(...) -> (text, raw, err).

    Step37: soft timeout + crash containment via safe_call(timeout_ms=...).
    """

    def __init__(self, *, name: str, provider: Any) -> None:
        self.name = str(name)
        self._provider = provider

    def _fingerprint_or_error(self) -> Tuple[Optional[str], Optional[str]]:
        """Return (fingerprint, error). Enforces Step92: fingerprint required for trace."""
        try:
            fp_fn = getattr(self._provider, "fingerprint", None)
            if fp_fn is None or not callable(fp_fn):
                return None, "provider_missing_fingerprint"
            fp = fp_fn()
            if not isinstance(fp, str) or not fp:
                return None, "provider_invalid_fingerprint"
            return fp, None
        except Exception as e:  # noqa: BLE001
            return None, f"provider_fingerprint_error:{type(e).__name__}:{e}"

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> WorkerResult:
        def _call_provider() -> Any:
            return self._provider.generate_text(
                prompt=prompt,
                temperature=float(temperature),
                max_output_tokens=int(max_output_tokens),
                instructions=instructions,
            )

        res = safe_call(fn=_call_provider, timeout_ms=timeout_ms)

        if res.ok:
            try:
                v = res.value  # type: ignore[misc]
                if isinstance(v, ProviderResult):
                    # New AI-PROVIDER envelope
                    success = bool(v.success)
                    text = "" if v.text is None else str(v.text)
                    raw = v.raw if isinstance(v.raw, dict) else {}
                    error = None if v.success else (v.error or v.reason_code or "provider_error")

                    fp, fp_err = self._fingerprint_or_error()
                    if fp is not None:
                        raw = dict(raw)
                        raw["provider_fingerprint"] = fp
                        raw["provider_name"] = self.name
                    if fp_err is not None:
                        # Enforce fingerprint presence/validity for traceability (Step92).
                        success = False
                        error = fp_err
                else:
                    # Legacy provider contract: (text, raw, err)
                    text, raw, err = v  # type: ignore[misc]
                    success = err is None
                    error = None if err is None else f"{type(err).__name__}: {err}"
                    if not isinstance(raw, dict):
                        raw = {}
                    if not isinstance(text, str):
                        text = str(text)

                    fp, fp_err = self._fingerprint_or_error()
                    if fp is not None:
                        raw = dict(raw)
                        raw["provider_fingerprint"] = fp
                        raw["provider_name"] = self.name
                    if fp_err is not None:
                        success = False
                        error = fp_err
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
    return ProviderTextWorker(name=name, provider=provider)
