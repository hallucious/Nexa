from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest

from src.platform.plugin_contract import ProviderKey, normalize_meta, ReasonCode


def test_step31_provider_key_allows_min_set() -> None:
    for v in (ProviderKey.GPT.value, ProviderKey.GEMINI.value, ProviderKey.LOCAL.value, ProviderKey.NONE.value):
        meta = normalize_meta({}, reason_code=ReasonCode.SUCCESS, provider=v, source="test")
        assert meta["provider"] == v


def test_step31_provider_key_rejects_unknown_under_pytest() -> None:
    with pytest.raises(ValueError):
        normalize_meta({}, reason_code=ReasonCode.SUCCESS, provider="openai", source="test")
