from __future__ import annotations

import inspect
from typing import Any, Dict, Optional

from src.contracts.provider_contract import (
    ProviderError,
    ProviderRequest,
    ProviderResult as EngineProviderResult,
)
from src.platform.provider_registry import ProviderRegistry
from src.providers.provider_adapter_contract import (
    ProviderMetrics,
    ProviderResult as AdapterProviderResult,
)


class GenerateTextProviderBridge:
    """Shared bridge from ``generate_text(...)`` providers into the runtime
    ``execute(request)`` contract.

    This keeps CLI real-provider registration and savefile provider building on
    the same practical adapter path instead of duplicating wrapper logic.
    """

    def __init__(self, provider: Any, provider_name: str | None = None) -> None:
        self.provider = provider
        self.provider_name = provider_name or type(provider).__name__

    @staticmethod
    def _sanitize_prompt(prompt: Any) -> str:
        return (str(prompt or "")).encode("utf-8", errors="ignore").decode("utf-8")

    @staticmethod
    def _build_generate_text_kwargs(request: ProviderRequest) -> Dict[str, Any]:
        options = dict(request.options or {})
        kwargs: Dict[str, Any] = {
            "prompt": GenerateTextProviderBridge._sanitize_prompt(request.prompt),
            "temperature": options.get("temperature", 0.0),
            "max_output_tokens": options.get("max_output_tokens", options.get("max_tokens", 1024)),
        }
        if options.get("instructions") is not None:
            kwargs["instructions"] = options.get("instructions")
        if options.get("timeout_sec") is not None:
            kwargs["timeout_sec"] = options.get("timeout_sec")
        if options.get("stream") is not None:
            kwargs["stream"] = bool(options.get("stream"))
        return kwargs

    @staticmethod
    def _filter_supported_kwargs(method: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            return kwargs

        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
            return kwargs

        allowed = set(signature.parameters.keys())
        return {key: value for key, value in kwargs.items() if key in allowed}

    def execute(self, request: ProviderRequest) -> EngineProviderResult:
        if not hasattr(self.provider, "generate_text"):
            raise TypeError(
                f"Provider '{self.provider_name}' must expose generate_text(...) for GenerateTextProviderBridge"
            )

        kwargs = self._filter_supported_kwargs(
            self.provider.generate_text,
            self._build_generate_text_kwargs(request),
        )

        try:
            raw_result = self.provider.generate_text(**kwargs)
        except Exception as exc:
            return EngineProviderResult(
                output=None,
                raw_text=None,
                structured=None,
                artifacts=[],
                trace={"provider": self.provider_name},
                error=ProviderError(
                    type="provider_internal_error",
                    message=str(exc),
                    retryable=False,
                ),
                stream=None,
            )

        return self._normalize_generate_text_result(raw_result)

    def _normalize_generate_text_result(self, raw_result: Any) -> EngineProviderResult:
        if isinstance(raw_result, EngineProviderResult):
            return raw_result

        if isinstance(raw_result, AdapterProviderResult):
            return self._canonical_to_runtime_result(raw_result)

        if isinstance(raw_result, tuple) and len(raw_result) == 3:
            text, raw, err = raw_result
            trace = {"provider": self.provider_name}
            if err is not None:
                return EngineProviderResult(
                    output=text,
                    raw_text=None if text is None else str(text),
                    structured=dict(raw) if isinstance(raw, dict) else None,
                    artifacts=[],
                    trace=trace,
                    error=ProviderError(
                        type="provider_internal_error",
                        message=str(err),
                        retryable=False,
                    ),
                    stream=dict(raw.get("stream")) if isinstance(raw, dict) and isinstance(raw.get("stream"), dict) else None,
                )
            return EngineProviderResult(
                output=text,
                raw_text=None if text is None else str(text),
                structured=dict(raw) if isinstance(raw, dict) else None,
                artifacts=[],
                trace=trace,
                error=None,
                stream=dict(raw.get("stream")) if isinstance(raw, dict) and isinstance(raw.get("stream"), dict) else None,
            )

        return EngineProviderResult(
            output=raw_result,
            raw_text=str(raw_result) if raw_result is not None else None,
            structured=None,
            artifacts=[],
            trace={"provider": self.provider_name},
            error=None,
            stream=None,
        )

    def _canonical_to_runtime_result(
        self,
        result: AdapterProviderResult,
    ) -> EngineProviderResult:
        raw = dict(result.raw) if isinstance(result.raw, dict) else {}
        trace = raw.get("trace") if isinstance(raw.get("trace"), dict) else {}
        trace = {"provider": self.provider_name, **trace}
        artifacts = raw.get("artifacts") if isinstance(raw.get("artifacts"), list) else []
        structured = raw.get("structured") if isinstance(raw.get("structured"), dict) else None
        output = raw.get("output")
        if output is None:
            output = result.text
        error = None
        if not result.success:
            error = ProviderError(
                type=str(result.reason_code or "provider_internal_error"),
                message=str(result.error or "provider execution failed"),
                retryable=False,
            )
        return EngineProviderResult(
            output=output,
            raw_text=result.text,
            structured=structured,
            artifacts=list(artifacts),
            trace=trace,
            error=error,
            stream=dict(raw.get("stream")) if isinstance(raw.get("stream"), dict) else None,
        )


class ProviderExecutor:
    """
    Execute provider calls through ProviderRegistry and normalize results
    into the canonical provider-adapter result contract.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    def execute(self, request: ProviderRequest) -> AdapterProviderResult:
        provider = self.registry.resolve(request.provider_id)

        if not hasattr(provider, "execute"):
            raise TypeError(
                f"Provider '{request.provider_id}' must expose execute(request)"
            )

        raw_result = provider.execute(request)
        return self._canonicalize_result(raw_result, request=request)

    def _canonicalize_result(self, raw_result: Any, *, request: ProviderRequest) -> AdapterProviderResult:
        if isinstance(raw_result, AdapterProviderResult):
            return self._canonicalize_canonical_result(raw_result)

        if isinstance(raw_result, EngineProviderResult):
            return self._canonicalize_runtime_result(raw_result, request=request)

        if isinstance(raw_result, dict):
            if self._looks_canonical(raw_result):
                return self._canonicalize_canonical_dict(raw_result)
            return self._canonicalize_runtime_dict(raw_result, request=request)

        return AdapterProviderResult(
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

    def _canonicalize_canonical_result(self, result: AdapterProviderResult) -> AdapterProviderResult:
        raw = result.raw if isinstance(result.raw, dict) else {}
        return AdapterProviderResult(
            success=bool(result.success),
            text=result.text,
            raw=raw,
            error=None if result.error is None else str(result.error),
            reason_code=None if result.reason_code is None else str(result.reason_code),
            metrics=self._coerce_metrics(result.metrics),
        )

    def _canonicalize_canonical_dict(self, payload: Dict[str, Any]) -> AdapterProviderResult:
        raw = payload.get("raw")
        if not isinstance(raw, dict):
            raw = {}
        return AdapterProviderResult(
            success=bool(payload.get("success", False)),
            text=payload.get("text"),
            raw=raw,
            error=None if payload.get("error") is None else str(payload.get("error")),
            reason_code=None if payload.get("reason_code") is None else str(payload.get("reason_code")),
            metrics=self._coerce_metrics(payload.get("metrics")),
        )

    def _canonicalize_runtime_result(
        self,
        result: EngineProviderResult,
        *,
        request: ProviderRequest,
    ) -> AdapterProviderResult:
        raw: Dict[str, Any] = {
            "provider_id": request.provider_id,
            "output": result.output,
            "trace": dict(result.trace or {}),
            "artifacts": list(result.artifacts or []),
        }
        if isinstance(result.stream, dict):
            raw["stream"] = dict(result.stream)
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

        return AdapterProviderResult(
            success=result.error is None,
            text=text,
            raw=raw,
            error=error,
            reason_code=reason_code,
            metrics=ProviderMetrics(latency_ms=0),
        )

    def _canonicalize_runtime_dict(self, payload: Dict[str, Any], *, request: ProviderRequest) -> AdapterProviderResult:
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

        standard = {"output", "raw_text", "structured", "artifacts", "trace", "error", "metrics", "stream"}
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

        return AdapterProviderResult(
            success=error_text is None,
            text=text,
            raw=raw,
            error=error_text,
            reason_code=reason_code,
            metrics=self._coerce_metrics(payload.get("metrics")),
        )
