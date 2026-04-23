"""
decision_policy.py

Validation Decision Policy for the Nexa Execution Engine.

Responsibility boundary:
    validators     → produce ValidationResult (facts about the engine/circuit)
    decision_policy → map ValidationResults to ValidationDecision (what to do)
    engine/runtime  → act on ValidationDecision (gate, record, finalize)

This module knows nothing about how execution works.
It only inspects ValidationResult objects and returns decisions.

Decision rules (v1):
    Pre-decision:
        structural failure              → BLOCK
        strict determinism failure      → BLOCK
        all pre-checks passed           → CONTINUE

    Post-decision:
        post-validation not performed   → ACCEPT  (strict mode: no post phase)
        post-validation success         → ACCEPT
        post-validation with violations → WARN    (advisory only)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .result import ValidationDecision, ValidationResult


@dataclass(frozen=True)
class PreDecisionResult:
    """Outcome of the pre-execution decision step."""

    decision: ValidationDecision
    # Human-readable reason (for trace metadata)
    reason: str

    @property
    def blocks_execution(self) -> bool:
        return self.decision.is_blocking


@dataclass(frozen=True)
class PostDecisionResult:
    """Outcome of the post-execution decision step."""

    decision: ValidationDecision
    reason: str


class ValidationDecisionPolicy:
    """Stateless policy that maps ValidationResults to ValidationDecisions.

    All methods are pure: same inputs always produce same outputs.
    No side effects. No engine knowledge.
    """

    def decide_pre(
        self,
        structural_result: ValidationResult,
        pre_determinism_result: Optional[ValidationResult],
    ) -> PreDecisionResult:
        """Map pre-execution validation results to a pre-decision.

        Rules:
            - Structural failure → BLOCK
            - Strict determinism failure (pre_determinism_result present and failed) → BLOCK
            - Otherwise → CONTINUE

        Args:
            structural_result: Result from StructuralValidator (always present).
            pre_determinism_result: Result from DeterminismValidator in strict
                mode. None when not in strict mode (determinism runs post).

        Returns:
            PreDecisionResult with BLOCK or CONTINUE.
        """
        if not structural_result.success:
            return PreDecisionResult(
                decision=ValidationDecision.BLOCK,
                reason="structural validation failed",
            )

        if pre_determinism_result is not None and not pre_determinism_result.success:
            return PreDecisionResult(
                decision=ValidationDecision.BLOCK,
                reason="strict determinism pre-validation failed",
            )

        return PreDecisionResult(
            decision=ValidationDecision.CONTINUE,
            reason="pre-validation passed",
        )

    def decide_post(
        self,
        post_determinism_result: Optional[ValidationResult],
        *,
        strict_determinism: bool,
    ) -> PostDecisionResult:
        """Map post-execution validation results to a post-decision.

        Rules:
            - post_determinism_result is None (strict mode, no post phase) → ACCEPT
            - post-validation succeeded with no violations              → ACCEPT
            - post-validation has violations (all advisory in non-strict) → WARN

        Args:
            post_determinism_result: Result from post-execution DeterminismValidator.
                None when strict mode was used (no post phase in that path).
            strict_determinism: Whether strict mode was active (informational).

        Returns:
            PostDecisionResult with ACCEPT or WARN.
        """
        if post_determinism_result is None:
            return PostDecisionResult(
                decision=ValidationDecision.ACCEPT,
                reason="post-validation not performed (strict mode path)",
            )

        if post_determinism_result.violations:
            return PostDecisionResult(
                decision=ValidationDecision.WARN,
                reason="advisory determinism violations detected",
            )

        return PostDecisionResult(
            decision=ValidationDecision.ACCEPT,
            reason="post-validation passed with no violations",
        )
