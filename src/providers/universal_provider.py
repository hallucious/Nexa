from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.providers.provider_contract import (
    ProviderRequest,
    ProviderResult,
    compute_provider_fingerprint,
    make_failure,
    make_success,
    map_exception_to_reason_code,
)
from src.providers.safe_mode import apply_safe_mode_prefix, run_safe_mode

from src.providers.adapters.base_adapter import ProviderAdapter
from src.providers.router import RETRYABLE_REASON_CODES, RoutingError, route_adapters


@dataclass
class UniversalProvider:
    """A single provider implementation delegating vendor specifics to adapters."""

    adapter: ProviderAdapter
    fallback_adapters: Optional[List[ProviderAdapter]] = None
    safe_mode_enabled: bool = True

    def fingerprint(self) -> str:
        info: Dict[str, Any] = {
            "provider": type(self).__name__,
            "safe_mode": bool(self.safe_mode_enabled),
        }
        try:
            info.update(self.adapter.fingerprint_components())
        except Exception:
            info["adapter"] = getattr(self.adapter, "name", "unknown")
        return compute_provider_fingerprint(info)

    def _adapters(self) -> List[ProviderAdapter]:
        adapters: List[ProviderAdapter] = [self.adapter]
        if self.fallback_adapters:
            adapters.extend(list(self.fallback_adapters))
        return adapters

    def _call_once(
        self,
        *,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
        model: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any], Optional[int]]:
        req = ProviderRequest(
            prompt=prompt,
            temperature=float(temperature),
            max_output_tokens=int(max_output_tokens),
            model=model,
        )
        text, raw, tokens_used, _attempts = route_adapters(req=req, adapters=self._adapters())
        return text, raw, tokens_used

    def _call_once_streaming(
        self,
        *,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
        model: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any], Optional[int]]:
        req = ProviderRequest(
            prompt=prompt,
            temperature=float(temperature),
            max_output_tokens=int(max_output_tokens),
            model=model,
        )

        last_exc: Optional[BaseException] = None
        for adapter in self._adapters():
            try:
                payload = adapter.build_payload(req)
                chunks = list(adapter.stream(payload))
                text_parts: List[str] = []
                tokens_used: Optional[int] = None
                raw: Dict[str, Any] = {}
                native_stream = False
                for chunk in chunks:
                    if not isinstance(chunk, dict):
                        continue
                    text_piece = chunk.get("text")
                    if isinstance(text_piece, str) and text_piece:
                        text_parts.append(text_piece)
                    if chunk.get("tokens_used") is not None:
                        tokens_used = chunk.get("tokens_used")
                    if isinstance(chunk.get("raw"), dict):
                        raw = dict(chunk["raw"])
                    native_stream = native_stream or bool(chunk.get("native_stream"))

                final_text = "".join(text_parts).strip()
                if not final_text and isinstance(raw, dict):
                    final_text, parsed_tokens = adapter.parse(raw)
                    if tokens_used is None:
                        tokens_used = parsed_tokens

                raw = dict(raw or {})
                raw["stream"] = {
                    "engaged": True,
                    "chunk_count": len(chunks),
                    "chunks": [dict(chunk) for chunk in chunks if isinstance(chunk, dict)],
                    "partial_output": final_text,
                    "native_stream": native_stream,
                }
                return final_text, raw, tokens_used
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                reason = map_exception_to_reason_code(exc)
                if reason not in RETRYABLE_REASON_CODES:
                    raise

        raise RoutingError(f"All adapters failed during streaming (last_error={type(last_exc).__name__ if last_exc else 'none'})")

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
        stream: bool = False,
    ) -> ProviderResult:
        _ = instructions

        if prompt is None:
            prompt = ""

        # SAFE_MODE prefix is applied inside run_safe_mode(), but we also keep
        # a stable behavior when SAFE_MODE is globally disabled via env.
        prompt_before = prompt
        latency_ms = 0

        last_raw: Dict[str, Any] = {}
        last_tokens: Optional[int] = None

        try:
            start = time.perf_counter()

            def call_fn(p: str) -> str:
                nonlocal last_raw, last_tokens
                if stream:
                    text, raw, tokens_used = self._call_once_streaming(
                        prompt=p,
                        temperature=float(temperature),
                        max_output_tokens=int(max_output_tokens),
                    )
                else:
                    text, raw, tokens_used = self._call_once(
                        prompt=p,
                        temperature=float(temperature),
                        max_output_tokens=int(max_output_tokens),
                    )
                last_raw = raw
                last_tokens = tokens_used
                return text

            if self.safe_mode_enabled:
                sm = run_safe_mode(prompt_before, call_fn)
                text_out = (sm.text or "").strip()
            else:
                # No SAFE_MODE wrapper; still respect optional prefix gate.
                p = apply_safe_mode_prefix(prompt_before)
                if stream:
                    text_out, last_raw, last_tokens = self._call_once_streaming(
                        prompt=p,
                        temperature=float(temperature),
                        max_output_tokens=int(max_output_tokens),
                    )
                else:
                    text_out, last_raw, last_tokens = self._call_once(
                        prompt=p,
                        temperature=float(temperature),
                        max_output_tokens=int(max_output_tokens),
                    )
                text_out = (text_out or "").strip()

            latency_ms = int((time.perf_counter() - start) * 1000.0)
            return make_success(text=text_out, raw=last_raw, latency_ms=latency_ms, tokens_used=last_tokens)
        except Exception as e:  # noqa: BLE001
            return make_failure(
                error=f"{type(e).__name__}: {e}",
                raw=last_raw or {},
                reason_code=map_exception_to_reason_code(e),
                latency_ms=latency_ms,
            )
