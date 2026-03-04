from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.providers.provider_contract import ProviderRequest, map_exception_to_reason_code
from src.providers.adapters.base_adapter import ProviderAdapter


@dataclass(frozen=True)
class RoutingAttempt:
    attempt_index: int
    adapter_name: str
    result: str  # "success" | "failure"
    retryable: bool
    reason_code: Optional[str]
    error_type: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_index": self.attempt_index,
            "adapter_name": self.adapter_name,
            "result": self.result,
            "retryable": self.retryable,
            "reason_code": self.reason_code,
            "error_type": self.error_type,
        }


class RoutingError(RuntimeError):
    pass


# Minimal retryable set aligned with provider_contract.map_exception_to_reason_code().
#
# - AI.timeout: transient timeout
# - AI.provider_error: vendor/network/http errors when status is known (includes 429/5xx)
RETRYABLE_REASON_CODES = {
    "AI.timeout",
    "AI.provider_error",
}


def _adapter_name(a: ProviderAdapter) -> str:
    return getattr(a, "name", type(a).__name__)


def route_adapters(
    *,
    req: ProviderRequest,
    adapters: Iterable[ProviderAdapter],
) -> Tuple[str, Dict[str, Any], Optional[int], List[RoutingAttempt]]:
    """Ordered fallback routing across adapters.

    Returns:
        text, raw, tokens_used, attempts
    """
    attempts: List[RoutingAttempt] = []
    last_exc: Optional[BaseException] = None

    for idx, adapter in enumerate(list(adapters)):
        try:
            payload = adapter.build_payload(req)
            raw = adapter.send(payload)
            text, tokens_used = adapter.parse(raw)
            attempts.append(
                RoutingAttempt(
                    attempt_index=idx,
                    adapter_name=_adapter_name(adapter),
                    result="success",
                    retryable=False,
                    reason_code=None,
                    error_type=None,
                )
            )
            return (text, raw, tokens_used, attempts)
        except Exception as e:  # noqa: BLE001
            last_exc = e
            reason = map_exception_to_reason_code(e)
            retryable = reason in RETRYABLE_REASON_CODES
            attempts.append(
                RoutingAttempt(
                    attempt_index=idx,
                    adapter_name=_adapter_name(adapter),
                    result="failure",
                    retryable=retryable,
                    reason_code=reason,
                    error_type=type(e).__name__,
                )
            )
            if not retryable:
                raise

    raise RoutingError(f"All adapters failed (last_error={type(last_exc).__name__ if last_exc else 'none'})")
