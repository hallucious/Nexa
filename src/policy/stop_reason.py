from __future__ import annotations

from enum import Enum


class StopReason(str, Enum):
    """Standard STOP reasons (Engine/policy canonical location)."""

    STOP_REQUESTED = "STOP_REQUESTED"
    UNKNOWN = "UNKNOWN"

    POLICY = "POLICY"
    VALIDATION_FAIL = "VALIDATION_FAIL"

    PROVIDER_ERROR = "PROVIDER_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def is_valid_stop_reason(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        StopReason(value)
        return True
    except Exception:
        return False
