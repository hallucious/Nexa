from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import pytest

from src.providers.provider_contract import ProviderRequest
from src.providers.universal_provider import UniversalProvider


@dataclass
class _FailingTimeoutAdapter:
    name: str = "timeout_adapter"

    def build_payload(self, req: ProviderRequest) -> Dict[str, Any]:
        return {"prompt": req.prompt, "adapter": self.name}

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise TimeoutError("simulated timeout")

    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        raise AssertionError("parse must not be called on failing adapter")

    def fingerprint_components(self) -> Dict[str, Any]:
        return {"adapter": self.name}


@dataclass
class _SuccessAdapter:
    name: str = "success_adapter"

    def build_payload(self, req: ProviderRequest) -> Dict[str, Any]:
        return {"prompt": req.prompt, "adapter": self.name}

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "echo": payload, "adapter": self.name}

    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        return ("OK", None)

    def fingerprint_components(self) -> Dict[str, Any]:
        return {"adapter": self.name}


@dataclass
class _NonRetryableAdapter:
    name: str = "non_retryable_adapter"

    def build_payload(self, req: ProviderRequest) -> Dict[str, Any]:
        return {"prompt": req.prompt, "adapter": self.name}

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # maps to SYSTEM.unexpected_exception -> non-retryable
        raise ValueError("simulated fatal")

    def parse(self, raw: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        raise AssertionError("parse must not be called on failing adapter")

    def fingerprint_components(self) -> Dict[str, Any]:
        return {"adapter": self.name}


def test_step97_routing_timeout_fallback_success():
    p = UniversalProvider(
        adapter=_FailingTimeoutAdapter(),
        fallback_adapters=[_SuccessAdapter()],
        safe_mode_enabled=False,
    )
    res = p.generate_text(prompt="hi")
    assert res.success is True
    assert (res.text or "") == "OK"
    assert res.raw.get("adapter") == "success_adapter"


def test_step97_routing_non_retryable_stops():
    p = UniversalProvider(
        adapter=_NonRetryableAdapter(),
        fallback_adapters=[_SuccessAdapter()],
        safe_mode_enabled=False,
    )
    res = p.generate_text(prompt="hi")
    assert res.success is False
    # Non-retryable: should not reach success adapter
    assert res.raw == {}
