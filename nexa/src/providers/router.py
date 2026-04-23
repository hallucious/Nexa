from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.providers.provider_adapter_contract import ProviderRequest, map_exception_to_reason_code
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


@dataclass(frozen=True)
class RoutingReliabilitySummary:
    """Confidence / trust surface summarising routing attempt outcomes.

    Exposes per-run routing reliability as a first-class observable so that
    the UI and observability layer can surface adapter-level trust signals
    without coupling directly to the router's internal attempt list.
    """
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    retryable_failures: int
    non_retryable_failures: int
    # 0.0–1.0 fraction of attempts that succeeded
    success_rate: float
    # Names of adapters that were attempted (in order)
    attempted_adapters: Tuple[str, ...]
    # Name of the adapter that ultimately succeeded, or None if all failed
    winning_adapter: Optional[str]
    # Most recent non-retryable reason code if the run failed, else None
    terminal_reason_code: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "retryable_failures": self.retryable_failures,
            "non_retryable_failures": self.non_retryable_failures,
            "success_rate": self.success_rate,
            "attempted_adapters": list(self.attempted_adapters),
            "winning_adapter": self.winning_adapter,
            "terminal_reason_code": self.terminal_reason_code,
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


def summarize_routing_reliability(attempts: List[RoutingAttempt]) -> RoutingReliabilitySummary:
    """Derive a RoutingReliabilitySummary from a completed attempt list.

    Intended to be called after route_adapters() returns (or raises) so that
    the observability layer and UI can surface adapter-level trust signals
    without holding a reference to the raw attempt list.
    """
    total = len(attempts)
    successful = [a for a in attempts if a.result == "success"]
    failed = [a for a in attempts if a.result == "failure"]
    retryable = [a for a in failed if a.retryable]
    non_retryable = [a for a in failed if not a.retryable]

    success_rate = len(successful) / total if total > 0 else 0.0
    winning_adapter: Optional[str] = successful[0].adapter_name if successful else None

    terminal_reason_code: Optional[str] = None
    if non_retryable:
        terminal_reason_code = non_retryable[-1].reason_code
    elif not successful and failed:
        terminal_reason_code = failed[-1].reason_code

    return RoutingReliabilitySummary(
        total_attempts=total,
        successful_attempts=len(successful),
        failed_attempts=len(failed),
        retryable_failures=len(retryable),
        non_retryable_failures=len(non_retryable),
        success_rate=round(success_rate, 4),
        attempted_adapters=tuple(a.adapter_name for a in attempts),
        winning_adapter=winning_adapter,
        terminal_reason_code=terminal_reason_code,
    )
