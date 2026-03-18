from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest

from src.platform.worker import wrap_text_provider
from src.providers.provider_contract import ProviderResult, make_success


@dataclass
class _OkProvider:
    fp: str = "fp-abc"

    def fingerprint(self) -> str:
        return self.fp

    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
        instructions: Optional[str] = None,
    ) -> ProviderResult:
        return make_success(text="ok", raw={"prompt": prompt}, latency_ms=0)


class _NoFingerprintProvider:
    def generate_text(
        self,
        *,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
        instructions: Optional[str] = None,
    ) -> ProviderResult:
        return make_success(text="ok", raw={}, latency_ms=0)


def test_step92_worker_injects_provider_fingerprint_into_raw() -> None:
    w = wrap_text_provider(name="gpt", provider=_OkProvider(fp="fp-123"))
    res = w.generate_text(prompt="hi", temperature=0.0, max_output_tokens=16)

    assert res.success is True
    assert res.raw.get("provider_fingerprint") == "fp-123"
    assert res.raw.get("provider_name") == "gpt"


def test_step92_missing_fingerprint_is_treated_as_failure() -> None:
    w = wrap_text_provider(name="nope", provider=_NoFingerprintProvider())
    res = w.generate_text(prompt="hi", temperature=0.0, max_output_tokens=16)

    assert res.success is False
    assert isinstance(res.error, str) and "fingerprint" in res.error
