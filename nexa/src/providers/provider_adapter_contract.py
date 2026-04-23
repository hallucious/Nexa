from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    temperature: float = 0.0
    max_output_tokens: int = 1024
    stop: Optional[list[str]] = None
    seed: Optional[int] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ProviderMetrics:
    latency_ms: int
    tokens_used: Optional[int] = None


@dataclass(frozen=True)
class ProviderResult:
    """AI-PROVIDER contract envelope.

    Backwards compatibility:
    - Unpackable into (text, raw, err) so legacy call sites using
      `text, raw, err = provider.generate_text(...)` keep working.
    - Dict-like helpers via `to_dict()` and `.get()` for convenience.
    """

    success: bool
    text: Optional[str]
    raw: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    reason_code: Optional[str] = None
    metrics: ProviderMetrics = field(default_factory=lambda: ProviderMetrics(latency_ms=0))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "text": self.text,
            "raw": self.raw,
            "error": self.error,
            "reason_code": self.reason_code,
            "metrics": {"latency_ms": self.metrics.latency_ms, "tokens_used": self.metrics.tokens_used},
        }

    def get(self, key: str, default: Any = None) -> Any:  # noqa: A003
        return self.to_dict().get(key, default)

    def keys(self) -> Iterable[str]:
        return self.to_dict().keys()

    def items(self) -> Iterable[tuple[str, Any]]:
        return self.to_dict().items()

    def values(self) -> Iterable[Any]:
        return self.to_dict().values()

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def to_legacy_tuple(self) -> Tuple[str, Dict[str, Any], Optional[BaseException]]:
        if self.success:
            return (self.text or "", self.raw if isinstance(self.raw, dict) else {}, None)
        err = RuntimeError(self.error or "provider_error")
        return ("", self.raw if isinstance(self.raw, dict) else {}, err)

    def __iter__(self) -> Iterator[Any]:
        # Enables tuple-unpacking compatibility.
        t = self.to_legacy_tuple()
        yield t[0]
        yield t[1]
        yield t[2]


def _safe_str(obj: Any) -> str:
    try:
        return str(obj)
    except Exception:
        return "<unprintable>"


def map_exception_to_reason_code(exc: BaseException, *, http_status: Optional[int] = None, body_text: str = "") -> str:
    """Best-effort mapping into the minimum reason_code set.

    Providers may refine this mapping later; v1.0.0 requires at least these keys.
    """
    import socket

    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "AI.timeout"

    status = http_status
    if status is None and hasattr(exc, "code"):
        try:
            status = int(getattr(exc, "code"))
        except Exception:
            status = None

    body_l = (body_text or "").lower()
    if status is not None:
        if status in (400, 401, 403, 429) and any(k in body_l for k in ("policy", "safety", "refus", "content")):
            return "AI.policy_refusal"
        return "AI.provider_error"

    return "SYSTEM.unexpected_exception"


def make_success(*, text: str, raw: Dict[str, Any], latency_ms: int, tokens_used: Optional[int] = None) -> ProviderResult:
    return ProviderResult(
        success=True,
        text=text,
        raw=raw if isinstance(raw, dict) else {},
        error=None,
        reason_code=None,
        metrics=ProviderMetrics(latency_ms=int(latency_ms), tokens_used=tokens_used),
    )


def make_failure(*, error: str, raw: Optional[Dict[str, Any]], reason_code: str, latency_ms: int) -> ProviderResult:
    return ProviderResult(
        success=False,
        text=None,
        raw=raw if isinstance(raw, dict) else {},
        error=_safe_str(error),
        reason_code=reason_code,
        metrics=ProviderMetrics(latency_ms=int(latency_ms), tokens_used=None),
    )

# --- Provider identity / fingerprint (AI-PROVIDER v1.1.0) --------------------

import hashlib
import json


def _canonical_json(data: dict) -> str:
    """Deterministic JSON encoding for fingerprinting."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_provider_fingerprint(info: dict) -> str:
    """Return stable provider fingerprint as 'sha256:<hex>'.

    The input MUST NOT contain secrets (API keys, tokens, raw prompts).
    """
    payload = _canonical_json(info).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return f"sha256:{digest}"

