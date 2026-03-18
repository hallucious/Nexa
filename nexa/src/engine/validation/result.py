from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


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
