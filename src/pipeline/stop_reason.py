from __future__ import annotations

from enum import Enum


class StopReason(str, Enum):
    """Standard STOP reasons (contract).

    Notes
    - Values are strings to keep JSON serialization stable.
    - Gates SHOULD set meta["stop_reason"] to one of these values when returning Decision.STOP.
    - Gates MAY set meta["stop_detail"] with a human-readable explanation.
    """

    # Requested/expected STOPs
    STOP_REQUESTED = "STOP_REQUESTED"
    UNKNOWN = "UNKNOWN"  # model/provider returned unknown / inconclusive

    # Policy & validation
    POLICY = "POLICY"
    VALIDATION_FAIL = "VALIDATION_FAIL"

    # Failures
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def is_valid_stop_reason(value: object) -> bool:
    """Return True if value is a known StopReason string."""

    if not isinstance(value, str):
        return False
    try:
        StopReason(value)
        return True
    except Exception:
        return False
