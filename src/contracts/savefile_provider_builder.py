"""
savefile_provider_builder.py

Builds a ProviderRegistry from savefile resources.

Encoding fix:
    urllib.request sends HTTP headers via http.client which encodes them using
    latin-1. Any non-ASCII character in the Authorization header (api_key) or
    extra_headers causes a UnicodeEncodeError that surfaces as:
        SAFE_MODE failed: 'latin-1' codec can't encode characters

    Fix: sanitize api_key to pure ASCII before passing to GPTProvider.
"""

from src.platform.provider_registry import ProviderRegistry
from src.contracts.savefile_format import Savefile
from src.contracts.provider_contract import (
    ProviderRequest,
    ProviderResult as ContractProviderResult,
    ProviderError,
)


def _to_ascii_safe(s: str) -> str:
    """Strip all non-ASCII characters — prevents latin-1 HTTP header failures."""
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="ignore")
    return s.encode("ascii", errors="ignore").decode("ascii")


def _extract_text(raw_result) -> str:
    """Normalize any provider return shape to a plain Python string."""
    # providers.ProviderResult: .success + .text
    if hasattr(raw_result, "success") and hasattr(raw_result, "text"):
        if raw_result.success:
            return str(raw_result.text or "")
        return f"[PROVIDER ERROR] {raw_result.error or 'unknown error'}"

    # contracts.ProviderResult: .output
    if hasattr(raw_result, "output"):
        out = raw_result.output
        if isinstance(out, str):
            return out
        if isinstance(out, dict):
            if "text" in out:
                return str(out["text"])
            if "analysis" in out and isinstance(out["analysis"], dict):
                return str(out["analysis"].get("text", ""))
        return str(out or "")

    if isinstance(raw_result, dict):
        if "text" in raw_result:
            return str(raw_result["text"])
        if "analysis" in raw_result and isinstance(raw_result["analysis"], dict):
            return str(raw_result["analysis"].get("text", ""))
        return str(raw_result)

    if isinstance(raw_result, str):
        return raw_result

    return str(raw_result)


class _GPTProviderAdapter:
    """Wraps GPTProvider.generate_text() → ContractProviderResult.execute() interface.

    Also sanitizes the prompt to UTF-8 safe bytes to avoid any encoding
    surprises in the HTTP layer.
    """

    def __init__(self, gpt_provider):
        self._gpt = gpt_provider

    def execute(self, request: ProviderRequest) -> ContractProviderResult:
        opts = request.options or {}
        temperature = float(opts.get("temperature", 0.7))
        max_output_tokens = int(opts.get("max_output_tokens", 1024))
        instructions = opts.get("instructions")

        # Round-trip through UTF-8 to strip any surrogates / bad bytes.
        prompt = (request.prompt or "").encode("utf-8", errors="ignore").decode("utf-8")

        try:
            raw = self._gpt.generate_text(
                prompt=prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                instructions=instructions,
            )
        except Exception as exc:
            return ContractProviderResult(
                output={"text": f"[PROVIDER ERROR] {exc}"},
                raw_text=None,
                structured=None,
                artifacts=[],
                trace={"provider": "gpt", "error": str(exc)},
                error=ProviderError(type="execution_error", message=str(exc)),
            )

        if hasattr(raw, "success") and not raw.success:
            err_msg = str(getattr(raw, "error", "provider failure"))
            return ContractProviderResult(
                output={"text": f"[PROVIDER ERROR] {err_msg}"},
                raw_text=None,
                structured=None,
                artifacts=[],
                trace={"provider": "gpt", "error": err_msg},
                error=ProviderError(type="provider_failure", message=err_msg),
            )

        text = _extract_text(raw)
        return ContractProviderResult(
            output={"text": text},
            raw_text=text,
            structured=None,
            artifacts=[],
            trace={"provider": "gpt"},
            error=None,
        )


def build_provider_registry_from_savefile(savefile: Savefile) -> ProviderRegistry:
    registry = ProviderRegistry()

    for provider_id, provider_resource in savefile.resources.providers.items():
        provider_type = provider_resource.type

        if provider_type in ("openai", "gpt"):
            from src.providers.gpt_provider import GPTProvider
            import os
            # Sanitize to pure ASCII — urllib encodes Authorization header via latin-1.
            api_key = _to_ascii_safe(os.getenv("OPENAI_API_KEY", "").strip())
            model = provider_resource.model or "gpt-4o-mini"
            cfg = provider_resource.config or {}
            timeout_sec = int(cfg.get("timeout_sec", 60))
            gpt = GPTProvider(api_key=api_key, model=model, timeout_sec=timeout_sec)
            provider_instance = _GPTProviderAdapter(gpt)

        elif provider_type == "anthropic":
            from src.providers.anthropic_provider import AnthropicProvider
            provider_instance = AnthropicProvider(
                model=provider_resource.model,
                config=provider_resource.config,
            )

        elif provider_type == "test":
            provider_instance = _create_test_provider()

        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        registry.register(provider_id, provider_instance)

    return registry


def _create_test_provider():
    class TestProvider:
        def execute(self, request: ProviderRequest) -> ContractProviderResult:
            text = f"[TEST] {request.prompt}"
            return ContractProviderResult(
                output={"text": text},
                raw_text=text,
                structured=None,
                artifacts=[],
                trace={"provider": "test"},
                error=None,
            )
    return TestProvider()
