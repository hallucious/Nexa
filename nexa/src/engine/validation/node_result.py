"""
node_result.py

Node-level validation result types.

These are independent from the engine-level ValidationResult.
The node validation layer operates per-node, not per-engine-graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from .result import Violation


class NodeDecision(str, Enum):
    """Decision produced by the node-level decision policy.

    Values:
        CONTINUE — Node handler execution may proceed.
        FAIL     — Node handler must not execute; node is marked FAILURE.
    """

    CONTINUE = "CONTINUE"
    FAIL = "FAIL"

    @property
    def is_blocking(self) -> bool:
        """True if this decision prevents handler execution."""
        return self is NodeDecision.FAIL


@dataclass(frozen=True)
class NodeValidationResult:
    """Result of node-level validation.

    Fields:
        node_id:          The node being validated.
        success:          True when no blocking violations were found.
        applied_rule_ids: Rule IDs evaluated during validation.
        violations:       List of Violation objects found (may be empty).
    """

    node_id: str
    success: bool
    applied_rule_ids: List[str] = field(default_factory=list)
    violations: List[Violation] = field(default_factory=list)
