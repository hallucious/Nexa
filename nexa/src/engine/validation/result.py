from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ValidationDecision(str, Enum):
    """Decision produced by the validation decision policy.

    Maps validation outcomes to explicit runtime actions consumed by the engine.

    Values:
        BLOCK    — Execution must not proceed. Hard failure.
        CONTINUE — Execution may proceed. All pre-validation checks passed.
        WARN     — Post-execution advisory. Violations present but not blocking.
        ACCEPT   — Post-execution clean. No violations found.
    """

    BLOCK = "BLOCK"
    CONTINUE = "CONTINUE"
    WARN = "WARN"
    ACCEPT = "ACCEPT"

    @property
    def is_blocking(self) -> bool:
        return self is ValidationDecision.BLOCK


@dataclass(frozen=True)
class Violation:
    rule_id: str
    rule_name: str
    severity: Severity
    location_type: str  # engine | node | channel | flow
    location_id: Optional[str]
    message: str


@dataclass(frozen=True)
class ValidationResult:
    success: bool
    engine_revision: str
    structural_fingerprint: str
    applied_rule_ids: List[str] = field(default_factory=list)
    violations: List[Violation] = field(default_factory=list)
