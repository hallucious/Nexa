"""Validation Engine (v1 skeleton).

Enforces structural contracts defined in:
- docs/specs/validation_engine_contract.md
- docs/specs/validation_rule_catalog.md
"""

from .result import ValidationResult, Violation, Severity
from .validator import ValidationEngine
