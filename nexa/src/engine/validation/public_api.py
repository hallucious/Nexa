"""
public_api.py

Explicit public surface of engine.validation for cross-layer consumers.

Purpose
-------
The engine.validation sub-package is engine-internal by default.
However, circuit_runner needs a bounded set of shared validation types
and governance shapes to coordinate with the engine governance model.

This module is the only sanctioned import target for non-engine code.
All cross-layer consumers (e.g. src/circuit/circuit_runner.py) must
import from here, not from the internal modules directly.

Internal engine code continues to import directly from the sub-modules.

Exports
-------
Value types (result.py):
    Severity, ValidationDecision, ValidationResult, Violation

Decision policy (decision_policy.py):
    ValidationDecisionPolicy, PreDecisionResult, PostDecisionResult

Governance shapes (governance_shapes.py):
    build_pre_validation_block, build_post_validation_block,
    build_decision_block, violations_as_dicts
"""

from __future__ import annotations

from src.engine.validation.decision_policy import (
    PostDecisionResult,
    PreDecisionResult,
    ValidationDecisionPolicy,
)
from src.engine.validation.governance_shapes import (
    build_decision_block,
    build_post_validation_block,
    build_pre_validation_block,
    violations_as_dicts,
)
from src.engine.validation.result import (
    Severity,
    ValidationDecision,
    ValidationResult,
    Violation,
)

__all__ = [
    # value types
    "Severity",
    "ValidationDecision",
    "ValidationResult",
    "Violation",
    # decision policy
    "ValidationDecisionPolicy",
    "PreDecisionResult",
    "PostDecisionResult",
    # governance shapes
    "build_decision_block",
    "build_post_validation_block",
    "build_pre_validation_block",
    "violations_as_dicts",
]
