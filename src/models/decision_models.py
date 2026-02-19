from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Decision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    STOP = "STOP"

    @property
    def is_pass(self) -> bool:
        return self is Decision.PASS

    @property
    def is_fail(self) -> bool:
        return self is Decision.FAIL

    @property
    def is_stop(self) -> bool:
        return self is Decision.STOP


@dataclass(frozen=True)
class Transition:
    from_gate: str
    to_gate: str
    decision: Decision
    at: str  # ISO8601 string


@dataclass
class GateResult:
    decision: Decision
    message: str
    outputs: Dict[str, str]  # artifact_name -> relative path (within run dir)
    meta: Optional[Dict[str, Any]] = None
