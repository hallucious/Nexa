from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple

from src.pipeline.runner import GateContext
from src.platform.plugin_contract import ReasonCode, infer_reason_code, normalize_meta


class G7FinalReviewPlugin(Protocol):
    """Execution plugin for G7 final review."""

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Return (text, meta). Must not raise for normal operation."""


@dataclass
class _GPTAdapter:
    provider: Any
    provider_key: str
    source: str

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        # Support either generate_text(prompt) or generate(prompt)
        if hasattr(self.provider, "generate_text"):
            resp = self.provider.generate_text(prompt)  # type: ignore[attr-defined]
        elif hasattr(self.provider, "generate"):
            resp = self.provider.generate(prompt)  # type: ignore[attr-defined]
        else:
            meta = normalize_meta(
                {"error": "provider_missing_generate_method"},
                reason_code=ReasonCode.PROVIDER_MISSING,
                provider=self.provider_key,
                source=self.source,
            )
            return ("", meta)

        # Normalize to (text, meta)
        if isinstance(resp, str):
            meta = normalize_meta(
                {},
                reason_code=ReasonCode.SUCCESS,
                provider=self.provider_key,
                source=self.source,
            )
            return (resp, meta)

        if isinstance(resp, dict):
            text = str(resp.get("text") or resp.get("content") or resp.get("output") or "")
            meta = {k: v for k, v in resp.items() if k not in ("text", "content", "output")}
            rc = infer_reason_code(meta=meta)
            meta = normalize_meta(meta, reason_code=rc, provider=self.provider_key, source=self.source)
            return (text, meta)

        if isinstance(resp, (list, tuple)):
            text = str(resp[0]) if len(resp) >= 1 else ""
            meta: Dict[str, Any] = {"raw_type": type(resp).__name__, "raw_len": len(resp)}
            meta = normalize_meta(
                meta,
                reason_code=ReasonCode.CONTRACT_VIOLATION,
                provider=self.provider_key,
                source=self.source,
                error="provider_return_shape_unexpected",
            )
            return (text, meta)

        meta = normalize_meta(
            {"raw_type": type(resp).__name__},
            reason_code=ReasonCode.CONTRACT_VIOLATION,
            provider=self.provider_key,
            source=self.source,
            error="provider_return_shape_unexpected",
        )
        return (str(resp), meta)


@dataclass
class _WrappedPlugin:
    inner: Any
    provider_key: str
    source: str

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        try:
            text, meta = self.inner.generate(prompt)
        except Exception as e:
            meta = normalize_meta(
                {"error": f"plugin_generate_exception: {type(e).__name__}: {e}"},
                reason_code=ReasonCode.INTERNAL_ERROR,
                provider=self.provider_key,
                source=self.source,
            )
            return ("", meta)

        if not isinstance(meta, dict):
            meta = {"error": "plugin_meta_not_dict", "raw_meta_type": type(meta).__name__}
            rc = ReasonCode.CONTRACT_VIOLATION
        else:
            rc = infer_reason_code(meta=meta)

        meta = normalize_meta(meta, reason_code=rc, provider=self.provider_key, source=self.source)
        return (str(text or ""), meta)


def resolve_g7_final_review_plugin(ctx: GateContext) -> Optional[G7FinalReviewPlugin]:
    """Resolve plugin in a stable order.

    Priority:
    1) providers['g7_final_review'] (explicit plugin)
    2) providers['gpt'] (adapter)
    """

    providers = ctx.providers or {}

    plugin = providers.get("g7_final_review")
    if plugin is not None and hasattr(plugin, "generate"):
        return _WrappedPlugin(plugin, provider_key="g7_final_review", source="g7_final_review")  # type: ignore[return-value]

    gpt = providers.get("gpt")
    if gpt is not None:
        return _GPTAdapter(gpt, provider_key="gpt", source="g7_final_review")

    return None


def resolve(ctx: GateContext) -> Optional[G7FinalReviewPlugin]:
    """Unified entrypoint: resolve(ctx) -> optional final review plugin."""
    return resolve_g7_final_review_plugin(ctx)
