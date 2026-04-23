from __future__ import annotations

from src.platform.plugin_contract import ReasonCode, normalize_meta, ProviderKey, VendorKey


def test_step33_reason_code_has_policy_rejected() -> None:
    assert hasattr(ReasonCode, "POLICY_REJECTED")
    assert ReasonCode.POLICY_REJECTED.value == "POLICY_REJECTED"


def test_step33_normalize_meta_allows_policy_rejected() -> None:
    meta = normalize_meta(
        {},
        reason_code=ReasonCode.POLICY_REJECTED,
        provider=ProviderKey.GPT.value,
        vendor=VendorKey.OPENAI.value,
        source="test",
        detail_code="policy_block",
    )
    assert meta["reason_code"] == "POLICY_REJECTED"
    assert meta["detail_code"] == "policy_block"
