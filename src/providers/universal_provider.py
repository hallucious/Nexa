from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

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


@dataclass
class UniversalProvider:
    """A single provider implementation delegating vendor specifics to adapters."""

    adapter: ProviderAdapter
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
        payload = self.adapter.build_payload(req)
        raw = self.adapter.send(payload)
        text, tokens_used = self.adapter.parse(raw)
        return text, raw, tokens_used

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        instructions: Optional[str] = None,
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
