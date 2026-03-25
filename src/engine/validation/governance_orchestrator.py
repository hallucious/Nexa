"""
governance_orchestrator.py

EngineGovernanceOrchestrator — extracted from Engine.execute().

This module holds the 4 governance phases that previously lived inline in
Engine.execute(). Engine.execute() now delegates to this orchestrator instead
of owning the phases directly.

The same ValidationDecisionPolicy and ValidationEngine are used; nothing
changes about the governance contract. Only the ownership changes:
  - Engine.execute() calls orchestrate_pre() + orchestrate_post()
  - Engine no longer *owns* the governance logic inline

This extraction is the structural change that prevents duplicate ownership.
CircuitRunner uses the same orchestration pattern (different validator,
same decision policy).

Design rules:
  - Stateless; all results returned, not stored on self.
  - Engine-specific (uses Engine as the subject of validation).
  - Pure delegation target; no execution of nodes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.contracts.spec_versions import (
    ENGINE_EXECUTION_MODEL_VERSION,
    ENGINE_TRACE_MODEL_VERSION,
    VALIDATION_ENGINE_CONTRACT_VERSION,
    VALIDATION_RULE_CATALOG_VERSION,
)
from src.utils.time import now_utc_iso

from .decision_policy import PostDecisionResult, PreDecisionResult, ValidationDecisionPolicy
from .result import ValidationResult

if TYPE_CHECKING:
    from ..engine import Engine


@dataclass
class PreGovernanceResult:
    """
    Output of the pre-execution governance phases (1, 1b, decision).

    Consumed by Engine.execute() to decide whether to proceed.
    """

    structural_validation: ValidationResult
    pre_determinism_validation: Optional[ValidationResult]  # None when non-strict
    pre_decision: PreDecisionResult
    execution_allowed: bool
    primary_validation: ValidationResult  # structural, or det if strict-det failed


@dataclass
class PostGovernanceResult:
    """
    Output of the post-execution governance phases (3, 4-decision).

    Consumed by Engine.execute() for trace finalization.
    """

    post_determinism_validation: Optional[ValidationResult]  # None when strict
    post_decision: PostDecisionResult


class EngineGovernanceOrchestrator:
    """
    Orchestrates the 4 governance lifecycle phases for Engine.execute().

    Extracted from Engine.execute() so that Engine delegates governance
    rather than owning it inline. This prevents the governance logic from
    being duplicated across both the Engine path and any future paths.

    Phase 1   — Structural pre-validation      (always blocking)
    Phase 1b  — Determinism pre-validation     (strict mode only, blocking)
    Phase 2   — (Execution — NOT this class's concern)
    Phase 3   — Determinism post-validation    (non-strict, advisory)
    Phase 4   — (Trace finalization — called by Engine with results from here)

    Usage by Engine.execute():
        orchestrator = EngineGovernanceOrchestrator()
        pre = orchestrator.run_pre(engine, revision_id=..., strict_determinism=...)
        if not pre.execution_allowed:
            ... build blocked trace using pre ...
            return trace

        ... execute nodes ...

        post = orchestrator.run_post(engine, revision_id=...,
                                     strict_determinism=..., pre=pre)
        ... build final trace using pre + post ...
        return trace
    """

    def __init__(self) -> None:
        self._policy = ValidationDecisionPolicy()

    def run_pre(
        self,
        engine: "Engine",
        *,
        revision_id: str,
        strict_determinism: bool,
    ) -> PreGovernanceResult:
        """
        Run Phase 1 and Phase 1b governance (pre-execution).

        Returns PreGovernanceResult. Caller checks .execution_allowed.
        """
        from ..validation.validator import ValidationEngine

        validator = ValidationEngine()

        # Phase 1: Structural validation (always blocking)
        structural = validator.validate_structural(engine, revision_id=revision_id)

        # Phase 1b: Determinism validation (strict mode only, blocking)
        pre_det: Optional[ValidationResult] = None
        if strict_determinism:
            pre_det = validator.validate_determinism(
                engine, revision_id=revision_id, strict_determinism=True
            )

        # Pre-decision
        pre_decision = self._policy.decide_pre(structural, pre_det)
        execution_allowed = not pre_decision.blocks_execution

        # Determine primary validation for trace top-level fields
        if pre_det is not None and not pre_det.success:
            primary = pre_det
        else:
            primary = structural

        return PreGovernanceResult(
            structural_validation=structural,
            pre_determinism_validation=pre_det,
            pre_decision=pre_decision,
            execution_allowed=execution_allowed,
            primary_validation=primary,
        )

    def run_post(
        self,
        engine: "Engine",
        *,
        revision_id: str,
        strict_determinism: bool,
    ) -> PostGovernanceResult:
        """
        Run Phase 3 governance (post-execution, advisory in non-strict mode).

        Returns PostGovernanceResult. Caller uses this in trace finalization.
        """
        from ..validation.validator import ValidationEngine

        validator = ValidationEngine()

        post_det: Optional[ValidationResult] = None
        if not strict_determinism:
            post_det = validator.validate_determinism(
                engine, revision_id=revision_id, strict_determinism=False
            )

        post_decision = self._policy.decide_post(
            post_det, strict_determinism=strict_determinism
        )

        return PostGovernanceResult(
            post_determinism_validation=post_det,
            post_decision=post_decision,
        )

    # ── Trace metadata builders (previously static methods on Engine) ─────────

    @staticmethod
    def build_pre_validation_meta(pre: PreGovernanceResult) -> Dict[str, Any]:
        """Build trace.meta['pre_validation'] block."""
        structural = pre.structural_validation
        pre_det = pre.pre_determinism_validation

        block: Dict[str, Any] = {
            "structural": {
                "performed": True,
                "success": structural.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in structural.violations
                ],
            },
        }

        if pre_det is not None:
            block["determinism"] = {
                "performed": True,
                "strict_mode": True,
                "success": pre_det.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in pre_det.violations
                ],
            }
        else:
            block["determinism"] = {"performed": False}

        return block

    @staticmethod
    def build_post_validation_meta(
        post: PostGovernanceResult,
        strict_determinism: bool,
    ) -> Dict[str, Any]:
        """Build trace.meta['post_validation'] block."""
        post_det = post.post_determinism_validation
        if post_det is not None:
            return {
                "performed": True,
                "strict_mode": strict_determinism,
                "success": post_det.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in post_det.violations
                ],
            }
        return {"performed": False}

    @staticmethod
    def build_decision_meta(
        pre: PreGovernanceResult,
        post: PostGovernanceResult,
    ) -> Dict[str, Any]:
        """Build trace.meta['decision'] block."""
        return {
            "pre": {
                "value": pre.pre_decision.decision.value,
                "reason": pre.pre_decision.reason,
            },
            "post": {
                "value": post.post_decision.decision.value,
                "reason": post.post_decision.reason,
            },
        }

    def build_legacy_validation_meta(
        self,
        pre: PreGovernanceResult,
        revision_id: str,
    ) -> Dict[str, Any]:
        """Build the legacy trace.meta['validation'] block for backward compat."""
        structural = pre.structural_validation
        return {
            "at": now_utc_iso(),
            "contract_version": VALIDATION_ENGINE_CONTRACT_VERSION,
            "rule_catalog_version": VALIDATION_RULE_CATALOG_VERSION,
            "snapshot": {
                "snapshot_version": "1",
                "applied_rules": sorted(
                    set(getattr(structural, "applied_rule_ids", []))
                ),
            },
        }
