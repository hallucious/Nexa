from __future__ import annotations

from src.contracts.provider_contract import (
    ProviderError,
    ProviderRequest,
    ProviderResult,
)
from src.platform.provider_registry import ProviderRegistry


class ProviderExecutor:
    """
    Execute provider calls through ProviderRegistry and normalize results
    into the ProviderResult contract.
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

        if isinstance(raw_result, ProviderResult):
            return raw_result

        if isinstance(raw_result, dict):
            error = raw_result.get("error")
            if isinstance(error, dict):
                error = ProviderError(
                    type=error.get("type", "provider_internal_error"),
                    message=error.get("message", "provider execution failed"),
                    retryable=bool(error.get("retryable", False)),
                )
            elif error is not None and not isinstance(error, ProviderError):
                error = ProviderError(
                    type="provider_internal_error",
                    message=str(error),
                    retryable=False,
                )

            standard = {"output", "raw_text", "structured", "artifacts", "trace", "error"}
            extras = {k: v for k, v in raw_result.items() if k not in standard}
            structured = raw_result.get("structured")
            if structured is None and extras:
                structured = extras

            return ProviderResult(
                output=raw_result.get("output"),
                raw_text=raw_result.get("raw_text"),
                structured=structured,
                artifacts=list(raw_result.get("artifacts", [])),
                trace=dict(raw_result.get("trace", {})),
                error=error,
            )

        return ProviderResult(
            output=raw_result,
            raw_text=str(raw_result) if raw_result is not None else None,
            structured=None,
            artifacts=[],
            trace={"provider_id": request.provider_id},
            error=None,
        )
