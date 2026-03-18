"""
node_validator.py

Node-level validator (v1 stub).

V1 behavior: always returns success=True with no violations.
This establishes the structural boundary for future node-level rules
without implementing any real rule logic yet.

Determinism guarantee:
    - Pure function.
    - No randomness.
    - No time-based behavior.
    - Same inputs always produce same output.
"""
from __future__ import annotations

from typing import Any, Dict

from .node_result import NodeValidationResult


class NodeValidator:
    """Node-level validator.

    V1 is a stub that always succeeds.  The interface is stable for future
    expansion to real per-node validation rules.

    Args to validate():
        node_id:         The node identifier.
        input_snapshot:  The input dict passed to the node.
        context:         Optional additional context (reserved for future use).
    """

    def validate(
        self,
        node_id: str,
        input_snapshot: Dict[str, Any],
        context: Dict[str, Any] | None = None,
    ) -> NodeValidationResult:
        """Validate a node before handler execution.

        V1: always succeeds; no rules are evaluated.

        Returns:
            NodeValidationResult with success=True and empty violations.
        """
        return NodeValidationResult(
            node_id=node_id,
            success=True,
            applied_rule_ids=[],
            violations=[],
        )
