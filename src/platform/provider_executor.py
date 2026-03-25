from __future__ import annotations

from typing import Any, Dict, Optional

from src.contracts.provider_contract import (
    ProviderError,
    ProviderRequest,
    ProviderResult as RuntimeProviderResult,
)
from src.platform.provider_registry import ProviderRegistry
from src.providers.provider_contract import (
    ProviderMetrics,
    ProviderResult,
)


class ProviderExecutor:
    """
    Execute provider calls through ProviderRegistry and normalize results
    into the canonical providers.ProviderResult contract.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    def execute(self, request: ProviderRequest) -> ProviderResult:
        provider = self.registry.resolve(request.provider_id)

        if not hasattr(provider, "execute"):
            raise TypeError(
                f"Provider '{request.provider_id}' must expose execute(request)"
            )

        raw_result = provider.execute(request)
        return self._canonicalize_result(raw_result, request=request)

    def _canonicalize_result(self, raw_result: Any, *, request: ProviderRequest) -> ProviderResult:
        if isinstance(raw_result, ProviderResult):
            return self._canonicalize_canonical_result(raw_result)

        if isinstance(raw_result, RuntimeProviderResult):
            return self._canonicalize_runtime_result(raw_result, request=request)

        if isinstance(raw_result, dict):
            if self._looks_canonical(raw_result):
                return self._canonicalize_canonical_dict(raw_result)
            return self._canonicalize_runtime_dict(raw_result, request=request)

        return ProviderResult(
            success=True,
            text=str(raw_result) if raw_result is not None else None,
            raw={"output": raw_result, "provider_id": request.provider_id},
            error=None,
            reason_code=None,
            metrics=ProviderMetrics(latency_ms=0),
        )

    @staticmethod
    def _looks_canonical(payload: Dict[str, Any]) -> bool:
        required = {"success", "text", "raw", "error", "reason_code", "metrics"}
        return required.issubset(set(payload.keys()))

    @staticmethod
    def _coerce_metrics(payload: Any) -> ProviderMetrics:
        if isinstance(payload, ProviderMetrics):
            return payload
        if isinstance(payload, dict):
            return ProviderMetrics(
                latency_ms=int(payload.get("latency_ms", 0) or 0),
                tokens_used=payload.get("tokens_used"),
            )
        return ProviderMetrics(latency_ms=0)

    def _canonicalize_canonical_result(self, result: ProviderResult) -> ProviderResult:
        raw = result.raw if isinstance(result.raw, dict) else {}
        return ProviderResult(
            success=bool(result.success),
            text=result.text,
            raw=raw,
            error=None if result.error is None else str(result.error),
            reason_code=None if result.reason_code is None else str(result.reason_code),
            metrics=self._coerce_metrics(result.metrics),
        )

    def _canonicalize_canonical_dict(self, payload: Dict[str, Any]) -> ProviderResult:
        raw = payload.get("raw")
        if not isinstance(raw, dict):
            raw = {}
        return ProviderResult(
            success=bool(payload.get("success", False)),
            text=payload.get("text"),
            raw=raw,
            error=None if payload.get("error") is None else str(payload.get("error")),
            reason_code=None if payload.get("reason_code") is None else str(payload.get("reason_code")),
            metrics=self._coerce_metrics(payload.get("metrics")),
        )

    def _canonicalize_runtime_result(
        self,
        result: RuntimeProviderResult,
        *,
        request: ProviderRequest,
    ) -> ProviderResult:
        raw: Dict[str, Any] = {
            "provider_id": request.provider_id,
            "output": result.output,
            "trace": dict(result.trace or {}),
            "artifacts": list(result.artifacts or []),
        }
        if isinstance(result.structured, dict):
            raw["structured"] = dict(result.structured)

        error = None
        reason_code = None
        if result.error is not None:
            error = str(result.error.message)
            reason_code = str(result.error.type)

        text = result.raw_text
        if text is None and isinstance(result.output, (str, int, float, bool)):
            text = str(result.output)

        return ProviderResult(
            success=result.error is None,
            text=text,
            raw=raw,
            error=error,
            reason_code=reason_code,
            metrics=ProviderMetrics(latency_ms=0),
        )

    def _canonicalize_runtime_dict(self, payload: Dict[str, Any], *, request: ProviderRequest) -> ProviderResult:
        error = payload.get("error")
        reason_code: Optional[str] = None
        error_text: Optional[str] = None
        if isinstance(error, dict):
            reason_code = str(error.get("type", "provider_internal_error"))
            error_text = str(error.get("message", "provider execution failed"))
        elif isinstance(error, ProviderError):
            reason_code = str(error.type)
            error_text = str(error.message)
        elif error is not None:
            reason_code = "provider_internal_error"
            error_text = str(error)

        standard = {"output", "raw_text", "structured", "artifacts", "trace", "error", "metrics"}
        extras = {k: v for k, v in payload.items() if k not in standard}
        structured = payload.get("structured")
        if structured is None and extras:
            structured = extras

        output = payload.get("output")
        text = payload.get("raw_text")
        if text is None and isinstance(output, (str, int, float, bool)):
            text = str(output)

        raw: Dict[str, Any] = dict(payload)
        raw.setdefault("provider_id", request.provider_id)
        raw.setdefault("output", output)
        raw["trace"] = dict(payload.get("trace", {}))
        raw["artifacts"] = list(payload.get("artifacts", []))
        if isinstance(structured, dict):
            raw["structured"] = dict(structured)

        return ProviderResult(
            success=error_text is None,
            text=text,
            raw=raw,
            error=error_text,
            reason_code=reason_code,
            metrics=self._coerce_metrics(payload.get("metrics")),
        )
