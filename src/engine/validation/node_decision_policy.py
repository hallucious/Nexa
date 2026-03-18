"""
node_decision_policy.py

Node-level validation decision policy.

Responsibility boundary:
    node_validator      → produces NodeValidationResult (facts about the node)
    node_decision_policy → maps NodeValidationResult → NodeDecision (what to do)
    engine/_run_node     → acts on NodeDecision (execute or mark FAILURE)

This module has no engine knowledge and no side effects.

Decision rules (v1):
    result.success == True  → CONTINUE
    result.success == False → FAIL
"""
from __future__ import annotations

from dataclasses import dataclass

from .node_result import NodeDecision, NodeValidationResult


@dataclass(frozen=True)
class NodeDecisionOutcome:
    """Outcome of the node-level decision step."""

    decision: NodeDecision
    reason: str

    @property
    def blocks_execution(self) -> bool:
        return self.decision.is_blocking


class NodeDecisionPolicy:
    """Stateless policy mapping NodeValidationResult → NodeDecision.

    All methods are pure: same inputs always produce same outputs.
    No side effects. No engine knowledge.
    """

    def decide(self, result: NodeValidationResult) -> NodeDecisionOutcome:
        """Map a node validation result to a node decision.

        Rules:
            success=True  → CONTINUE ("node validation passed")
            success=False → FAIL     ("node validation failed: <first violation>")

        Args:
            result: NodeValidationResult from NodeValidator.

        Returns:
            NodeDecisionOutcome with CONTINUE or FAIL and a non-empty reason.
        """
        if result.success:
            return NodeDecisionOutcome(
                decision=NodeDecision.CONTINUE,
                reason="node validation passed",
            )

        first_msg = result.violations[0].message if result.violations else "validation failed"
        return NodeDecisionOutcome(
            decision=NodeDecision.FAIL,
            reason=f"node validation failed: {first_msg}",
        )
