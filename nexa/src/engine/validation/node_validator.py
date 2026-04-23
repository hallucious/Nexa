"""
node_validator.py

Node-level validator — V1 with real validation rules.

Implemented rules:
    NODE-VAL-001 — Invalid node_id
    NODE-VAL-002 — Input snapshot must be dict
    NODE-VAL-003 — Reserved input key collision ("validation" / "decision")

Determinism guarantee:
    - Pure function.
    - No randomness.
    - No time-based behavior.
    - Same inputs always produce same output.
    - No engine knowledge beyond the supplied arguments.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .node_result import NodeValidationResult
from .result import Severity, Violation

# Reserved top-level keys in input_snapshot that collide with node trace metadata.
_RESERVED_INPUT_KEYS: frozenset = frozenset({"validation", "decision"})

# All rule IDs evaluated by this validator (for applied_rule_ids reporting).
_ALL_RULE_IDS: List[str] = ["NODE-VAL-001", "NODE-VAL-002", "NODE-VAL-003"]


class NodeValidator:
    """Node-level validator.

    Validates node_id and input_snapshot before handler execution.
    All methods are pure and deterministic.
    """

    def validate(
        self,
        node_id: Any,
        input_snapshot: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> NodeValidationResult:
        """Validate a node before handler execution.

        Evaluates all three V1 rules in order.  All rules are always
        evaluated; violations are accumulated rather than short-circuited.

        Rules:
            NODE-VAL-001  Invalid node_id (not a str, empty, or whitespace-only)
            NODE-VAL-002  Input snapshot must be a dict
            NODE-VAL-003  Reserved key collision in input_snapshot

        Args:
            node_id:        The node identifier (expected: non-empty str).
            input_snapshot: The input dict passed to the node (expected: dict).
            context:        Reserved for future use; not inspected in V1.

        Returns:
            NodeValidationResult with success=(len(violations)==0).
        """
        violations: List[Violation] = []

        # ── NODE-VAL-001: Invalid node_id ─────────────────────────────────────
        node_id_ok = isinstance(node_id, str) and node_id.strip() != ""
        if not node_id_ok:
            if not isinstance(node_id, str):
                msg = f"node_id must be a string, got {type(node_id).__name__!r}"
                loc: Optional[str] = None
            elif node_id == "":
                msg = "node_id must not be empty"
                loc = None
            else:
                msg = "node_id must not be whitespace-only"
                loc = None
            violations.append(
                Violation(
                    rule_id="NODE-VAL-001",
                    rule_name="Invalid node_id",
                    severity=Severity.ERROR,
                    location_type="node",
                    location_id=loc,
                    message=msg,
                )
            )

        # ── NODE-VAL-002: Input snapshot must be dict ──────────────────────────
        snapshot_is_dict = isinstance(input_snapshot, dict)
        if not snapshot_is_dict:
            violations.append(
                Violation(
                    rule_id="NODE-VAL-002",
                    rule_name="Input snapshot must be dict",
                    severity=Severity.ERROR,
                    location_type="node",
                    location_id=node_id if isinstance(node_id, str) and node_id.strip() else None,
                    message=(
                        f"input_snapshot must be a dict, "
                        f"got {type(input_snapshot).__name__!r}"
                    ),
                )
            )

        # ── NODE-VAL-003: Reserved key collision ───────────────────────────────
        # Only applicable when input_snapshot is a dict (otherwise NODE-VAL-002 fires).
        if snapshot_is_dict:
            node_loc = node_id if isinstance(node_id, str) and node_id.strip() else None
            for key in sorted(input_snapshot.keys()):  # sorted for determinism
                if key in _RESERVED_INPUT_KEYS:
                    violations.append(
                        Violation(
                            rule_id="NODE-VAL-003",
                            rule_name="Reserved input key collision",
                            severity=Severity.ERROR,
                            location_type="node",
                            location_id=node_loc,
                            message=(
                                f"input_snapshot contains reserved key {key!r}; "
                                "this collides with node trace metadata semantics"
                            ),
                        )
                    )

        return NodeValidationResult(
            node_id=str(node_id) if not isinstance(node_id, str) else node_id,
            success=len(violations) == 0,
            applied_rule_ids=list(_ALL_RULE_IDS),
            violations=violations,
        )
