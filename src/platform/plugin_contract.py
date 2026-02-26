from __future__ import annotations

"""Platform plugin contract helpers.

Step30: required meta keys + ReasonCode.
Step31: ProviderKey (routing key) + validation.
Step32: VendorKey (vendor identity) + validation.
Step33: Failure catalog taxonomy update: add POLICY_REJECTED (top-level category).

Compatibility guarantees:
- infer_reason_code is preserved.
- normalize_meta keeps call shape; vendor is optional with default 'none'.
"""

import os
from enum import Enum
from typing import Any, Dict, Optional, Union

CONTRACT_VERSION: str = "2.4"


class ReasonCode(str, Enum):
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    CAPABILITY_SELECTED = "CAPABILITY_SELECTED"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    CAPABILITY_REQUIRED_MISSING = "CAPABILITY_REQUIRED_MISSING"
    PROVIDER_MISSING = "PROVIDER_MISSING"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    POLICY_REJECTED = "POLICY_REJECTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ProviderKey(str, Enum):
    GPT = "gpt"
    GEMINI = "gemini"
    LOCAL = "local"
    NONE = "none"


class VendorKey(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    LOCAL = "local"
    NONE = "none"


REQUIRED_META_KEYS = ("reason_code", "provider", "vendor", "source", "contract_version")


def _as_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""


def _is_pytest() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _normalize_enum(value: Union[str, Enum], enum_cls: Any, field_name: str) -> Enum:
    if isinstance(value, enum_cls):
        return value

    v = _as_str(value).strip()
    if not v:
        return enum_cls("none")

    try:
        return enum_cls(v)
    except Exception:
        if _is_pytest():
            raise ValueError(f"{field_name}_invalid: {v}")
        return enum_cls("none")


def normalize_meta(
    meta: Optional[Dict[str, Any]],
    *,
    reason_code: ReasonCode,
    provider: Union[str, ProviderKey],
    source: str,
    error: Optional[str] = None,
    vendor: Union[str, VendorKey] = VendorKey.NONE,
    product: Optional[str] = None,
    model: Optional[str] = None,
    tool: Optional[str] = None,
    detail_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a meta dict that satisfies the required contract.

    - reason_code: top-level category (stable taxonomy).
    - detail_code: optional, concrete machine-friendly cause (Step33 recommendation).
    """

    out: Dict[str, Any] = dict(meta or {})

    provider_key = _normalize_enum(provider, ProviderKey, "provider_key")
    vendor_key = _normalize_enum(vendor, VendorKey, "vendor_key")

    out["reason_code"] = _as_str(reason_code.value)
    out["provider"] = _as_str(provider_key.value)
    out["vendor"] = _as_str(vendor_key.value)
    out["source"] = _as_str(source)
    out["contract_version"] = CONTRACT_VERSION

    if error:
        out.setdefault("error", _as_str(error))

    if detail_code is not None:
        out["detail_code"] = _as_str(detail_code)

    if product is not None:
        out["product"] = _as_str(product)
    if model is not None:
        out["model"] = _as_str(model)
    if tool is not None:
        out["tool"] = _as_str(tool)

    return out


def infer_reason_code(*, meta: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> ReasonCode:
    """Infer a ReasonCode from existing meta/error.

    Backward-compatible heuristic. Gate/policy layers may override with POLICY_REJECTED.
    """

    if error:
        e = error.lower()
        if "missing" in e:
            return ReasonCode.PROVIDER_MISSING
        if "policy" in e or "rejected" in e or "deny" in e:
            return ReasonCode.POLICY_REJECTED
        if "contract" in e or "provider_key_invalid" in e or "vendor_key_invalid" in e:
            return ReasonCode.CONTRACT_VIOLATION
        return ReasonCode.PROVIDER_ERROR

    if meta and isinstance(meta, dict):
        e0 = meta.get("error")
        if isinstance(e0, str) and e0.strip():
            e = e0.lower()
            if "missing" in e:
                return ReasonCode.PROVIDER_MISSING
            if "policy" in e or "rejected" in e or "deny" in e:
                return ReasonCode.POLICY_REJECTED
            if "contract" in e or "provider_key_invalid" in e or "vendor_key_invalid" in e:
                return ReasonCode.CONTRACT_VIOLATION
            return ReasonCode.PROVIDER_ERROR

        # If an upstream sets detail_code
        d = meta.get("detail_code")
        if isinstance(d, str) and d.strip():
            dl = d.lower()
            if dl.startswith("policy"):
                return ReasonCode.POLICY_REJECTED

    return ReasonCode.SUCCESS
