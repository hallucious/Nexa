from __future__ import annotations

import pytest

from src.platform.plugin_contract import (
    VendorKey,
    ProviderKey,
    ReasonCode,
    normalize_meta,
)


def test_step32_vendor_key_allows_min_set():
    for v in (
        VendorKey.OPENAI.value,
        VendorKey.GOOGLE.value,
        VendorKey.ANTHROPIC.value,
        VendorKey.PERPLEXITY.value,
        VendorKey.LOCAL.value,
        VendorKey.NONE.value,
    ):
        meta = normalize_meta(
            {},
            reason_code=ReasonCode.SUCCESS,
            provider=ProviderKey.GPT.value,
            vendor=v,
            source="test",
        )
        assert meta["vendor"] == v


def test_step32_vendor_key_rejects_unknown_under_pytest():
    with pytest.raises(ValueError):
        normalize_meta(
            {},
            reason_code=ReasonCode.SUCCESS,
            provider="gpt",
            vendor="unknown_vendor",
            source="test",
        )
