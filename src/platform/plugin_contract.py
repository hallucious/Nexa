from __future__ import annotations

"""Platform plugin contract helpers.

This module standardizes the *meta* payload produced by platform plugins.

Step30:
- Required meta keys + ReasonCode enum.
- infer_reason_code helper (kept for backward compatibility).

Step31:
- ProviderKey enum (minimal set) and validation/normalization.

Step32:
- VendorKey enum (vendor identity) separated from ProviderKey to avoid enum drift.
  Vendor defaults to 'none' if not specified.

Compatibility guarantees:
- infer_reason_code is preserved.
- normalize_meta keeps the previous call shape and adds optional vendor support.
"""

import os
from enum import Enum
from typing import Any, Dict, Optional, Union

# Contract version for meta payloads (mirrors doc minor version for contract changes).
CONTRACT_VERSION: str = "2.3"


class ReasonCode(str, Enum):
    """Allowed reason codes for plugin meta."""

    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    PROVIDER_MISSING = "PROVIDER_MISSING"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ProviderKey(str, Enum):
    """Routing/engine key (minimal set)."""

    GPT = "gpt"
    GEMINI = "gemini"
    LOCAL = "local"
    NONE = "none"


class VendorKey(str, Enum):
    """Vendor identity (separate from ProviderKey)."""

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    LOCAL = "local"
    NONE = "none"


# Required keys for any meta produced via normalize_meta.
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
        # All our enums include "none"
        return enum_cls("none")

    try:
        return enum_cls(v)
    except Exception:
        # Stability-first: fail fast under pytest
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
) -> Dict[str, Any]:
    """Return a meta dict that satisfies the required contract.

    Notes:
    - provider: routing/engine key (ProviderKey).
    - vendor: vendor identity (VendorKey), defaults to 'none'.
    - product/model/tool are optional identity fields (strings).

    Under pytest:
    - invalid provider/vendor values raise ValueError.
    """

    out: Dict[str, Any] = dict(meta or {})

    provider_key = _normalize_enum(provider, ProviderKey, "provider_key")
    vendor_key = _normalize_enum(vendor, VendorKey, "vendor_key")

    # Required keys
    out["reason_code"] = _as_str(reason_code.value)
    out["provider"] = _as_str(provider_key.value)
    out["vendor"] = _as_str(vendor_key.value)
    out["source"] = _as_str(source)
    out["contract_version"] = CONTRACT_VERSION

    # Optional canonical error key
    if error:
        out.setdefault("error", _as_str(error))

    # Optional identity fields
    if product is not None:
        out["product"] = _as_str(product)
    if model is not None:
        out["model"] = _as_str(model)
    if tool is not None:
        out["tool"] = _as_str(tool)

    return out


def infer_reason_code(*, meta: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> ReasonCode:
    """Infer a ReasonCode from existing meta/error.

    This helper is preserved for backward compatibility with earlier plugins.
    """

    if error:
        e = error.lower()
        if "missing" in e:
            return ReasonCode.PROVIDER_MISSING
        if "contract" in e or "provider_key_invalid" in e or "vendor_key_invalid" in e:
            return ReasonCode.CONTRACT_VIOLATION
        return ReasonCode.PROVIDER_ERROR

    if meta and isinstance(meta, dict):
        e0 = meta.get("error")
        if isinstance(e0, str) and e0.strip():
            e = e0.lower()
            if "missing" in e:
                return ReasonCode.PROVIDER_MISSING
            if "contract" in e or "provider_key_invalid" in e or "vendor_key_invalid" in e:
                return ReasonCode.CONTRACT_VIOLATION
            return ReasonCode.PROVIDER_ERROR

    return ReasonCode.SUCCESS
