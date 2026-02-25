from __future__ import annotations

"""Platform plugin contract helpers (Doc SemVer v2.x).

This module standardizes the *meta* payload produced by platform plugins.

Rationale:
- Meta is used for observability, failure cataloging, and regression analysis.
- A small set of required keys is enforced by tests to prevent drift.

Scope:
- Applies to plugin APIs that return a `meta: dict` (e.g., G4/G6/G7 plugin flows).
- Additional meta keys are allowed.
"""

from enum import Enum
from typing import Any, Dict, Optional


CONTRACT_VERSION: str = "2.1"


class ReasonCode(str, Enum):
    """Allowed reason codes for plugin meta."""

    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    PROVIDER_MISSING = "PROVIDER_MISSING"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    INTERNAL_ERROR = "INTERNAL_ERROR"


REQUIRED_META_KEYS = ("reason_code", "provider", "source", "contract_version")


def _as_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""


def normalize_meta(
    meta: Optional[Dict[str, Any]],
    *,
    reason_code: ReasonCode,
    provider: str,
    source: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a meta dict that satisfies the required contract."""

    out: Dict[str, Any] = dict(meta or {})

    # Required keys
    out["reason_code"] = _as_str(reason_code.value)
    out["provider"] = _as_str(provider)
    out["source"] = _as_str(source)
    out["contract_version"] = CONTRACT_VERSION

    # Optional canonical error key
    if error:
        out.setdefault("error", _as_str(error))

    return out


def infer_reason_code(*, meta: Optional[Dict[str, Any]], error: Optional[str] = None) -> ReasonCode:
    """Infer a ReasonCode from existing meta/error."""

    if error:
        if "missing" in error.lower():
            return ReasonCode.PROVIDER_MISSING
        if "contract" in error.lower():
            return ReasonCode.CONTRACT_VIOLATION
        return ReasonCode.PROVIDER_ERROR

    if meta and isinstance(meta, dict):
        e = meta.get("error")
        if isinstance(e, str) and e.strip():
            if "missing" in e.lower():
                return ReasonCode.PROVIDER_MISSING
            if "contract" in e.lower():
                return ReasonCode.CONTRACT_VIOLATION
            return ReasonCode.PROVIDER_ERROR

    return ReasonCode.SUCCESS
