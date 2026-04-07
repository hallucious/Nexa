"""designer_constraint_system.py

Designer AI Constraint System (precision track, v0.1).

Components:
  1. DesignerConstraintPolicy  — allowed/forbidden node/resource types
  2. CircuitLintResult         — lint output for a proposed circuit patch
  3. AutoCritiqueResult        — auto-critique of a designer proposal
  4. lint_circuit_proposal()   — entry point for lint
  5. critique_proposal()       — entry point for auto-critique

All designer work must pass: Constraint DSL → Lint → Critique → Preview → Approval → Commit.
This module covers the Constraint DSL, Lint, and Auto-Critique steps.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Forbidden patterns ─────────────────────────────────────────────────────

_FORBIDDEN_NODE_KINDS: set = {
    "pipeline_step",      # legacy pipeline concept
    "step_list",          # step-list workflow model
    "mutable_artifact",   # violates append-only rule
    "unrestricted_write", # violates plugin isolation
}

_FORBIDDEN_RESOURCE_COMBOS: List[tuple] = [
    # (resource_a, resource_b) — both present in same node = forbidden
    ("provider.any", "plugin.unrestricted_write"),
]

_REQUIRED_FOR_HIGH_RISK: set = {
    "verifier",
}


# ── Constraint policy ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class DesignerConstraintPolicy:
    policy_id: str
    allowed_node_kinds: List[str]
    allowed_resource_types: List[str]
    forbidden_node_kinds: List[str] = field(default_factory=list)
    forbidden_resource_patterns: List[str] = field(default_factory=list)
    mandatory_verifier_on_high_risk: bool = True
    max_node_depth: int = 20
    max_nodes_per_circuit: int = 50

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise DesignerConstraintError("policy_id must be non-empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "allowed_node_kinds": list(self.allowed_node_kinds),
            "allowed_resource_types": list(self.allowed_resource_types),
            "forbidden_node_kinds": list(self.forbidden_node_kinds),
            "forbidden_resource_patterns": list(self.forbidden_resource_patterns),
            "mandatory_verifier_on_high_risk": self.mandatory_verifier_on_high_risk,
            "max_node_depth": self.max_node_depth,
            "max_nodes_per_circuit": self.max_nodes_per_circuit,
        }


DEFAULT_CONSTRAINT_POLICY = DesignerConstraintPolicy(
    policy_id="default",
    allowed_node_kinds=["execution", "verification", "review_gate", "subcircuit"],
    allowed_resource_types=["prompt", "provider", "plugin", "verifier"],
    forbidden_node_kinds=list(_FORBIDDEN_NODE_KINDS),
    forbidden_resource_patterns=["plugin.unrestricted_write.*"],
    mandatory_verifier_on_high_risk=True,
    max_node_depth=20,
    max_nodes_per_circuit=50,
)


class DesignerConstraintError(ValueError):
    """Raised when a designer constraint invariant is violated."""


# ── Lint ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LintViolation:
    code: str
    message: str
    node_ref: Optional[str] = None
    severity: str = "error"  # "error" | "warning"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "node_ref": self.node_ref,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class CircuitLintResult:
    lint_id: str
    passed: bool
    violations: List[LintViolation]
    warnings: List[LintViolation]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lint_id": self.lint_id,
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "explanation": self.explanation,
        }


def lint_circuit_proposal(
    *,
    nodes: List[Dict[str, Any]],
    policy: DesignerConstraintPolicy = DEFAULT_CONSTRAINT_POLICY,
    lint_id: Optional[str] = None,
) -> CircuitLintResult:
    """Lint a proposed circuit (list of node dicts).

    Each node dict should have: id, kind, resources (list of resource type strings).
    """
    violations: List[LintViolation] = []
    warnings: List[LintViolation] = []

    if len(nodes) > policy.max_nodes_per_circuit:
        violations.append(LintViolation(
            code="CIRCUIT_TOO_LARGE",
            message=f"circuit has {len(nodes)} nodes; max={policy.max_nodes_per_circuit}",
        ))

    has_verifier = False
    high_risk_found = False

    for node in nodes:
        node_id = node.get("id", "<unknown>")
        kind = node.get("kind", "")
        resources = node.get("resources", [])

        # Forbidden node kind check
        if kind in policy.forbidden_node_kinds:
            violations.append(LintViolation(
                code="FORBIDDEN_NODE_KIND",
                message=f"node kind {kind!r} is forbidden by constraint policy",
                node_ref=node_id,
            ))

        # Allowed node kind check
        if policy.allowed_node_kinds and kind and kind not in policy.allowed_node_kinds:
            warnings.append(LintViolation(
                code="UNKNOWN_NODE_KIND",
                message=f"node kind {kind!r} not in allowed_node_kinds",
                node_ref=node_id,
                severity="warning",
            ))

        # Resource type check
        for res in resources:
            if res == "verifier":
                has_verifier = True
            res_type = res.split(".")[0] if "." in res else res
            if (
                policy.allowed_resource_types
                and res_type not in policy.allowed_resource_types
                and res not in policy.allowed_resource_types
            ):
                warnings.append(LintViolation(
                    code="UNKNOWN_RESOURCE_TYPE",
                    message=f"resource {res!r} not in allowed_resource_types",
                    node_ref=node_id,
                    severity="warning",
                ))
            for pattern in policy.forbidden_resource_patterns:
                pat_prefix = pattern.rstrip(".*")
                if res.startswith(pat_prefix):
                    violations.append(LintViolation(
                        code="FORBIDDEN_RESOURCE_PATTERN",
                        message=f"resource {res!r} matches forbidden pattern {pattern!r}",
                        node_ref=node_id,
                    ))

        # Dead-end node warning (no outputs defined and not a review_gate)
        if not node.get("outputs") and kind not in ("review_gate",):
            warnings.append(LintViolation(
                code="DEAD_END_NODE",
                message="node has no outputs defined",
                node_ref=node_id,
                severity="warning",
            ))

        if node.get("risk_level") in ("high", "restricted"):
            high_risk_found = True

    # High-risk path requires verifier
    if high_risk_found and policy.mandatory_verifier_on_high_risk and not has_verifier:
        violations.append(LintViolation(
            code="HIGH_RISK_MISSING_VERIFIER",
            message="high-risk nodes detected but no verifier node found in circuit",
        ))

    passed = len(violations) == 0
    explanation = (
        f"lint {'passed' if passed else 'failed'}; "
        f"{len(violations)} violation(s), {len(warnings)} warning(s)"
    )

    return CircuitLintResult(
        lint_id=lint_id or str(uuid.uuid4()),
        passed=passed,
        violations=violations,
        warnings=warnings,
        explanation=explanation,
    )


# ── Auto-Critique ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CritiqueNote:
    code: str
    message: str
    severity: str = "warning"  # "warning" | "info"

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass(frozen=True)
class AutoCritiqueResult:
    critique_id: str
    overall_verdict: str  # "safe" | "overbuilt" | "unsafe" | "ambiguous"
    notes: List[CritiqueNote]
    safer_alternative_suggested: bool
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "critique_id": self.critique_id,
            "overall_verdict": self.overall_verdict,
            "notes": [n.to_dict() for n in self.notes],
            "safer_alternative_suggested": self.safer_alternative_suggested,
            "explanation": self.explanation,
        }


def critique_proposal(
    *,
    nodes: List[Dict[str, Any]],
    user_request_summary: str = "",
    policy: DesignerConstraintPolicy = DEFAULT_CONSTRAINT_POLICY,
    critique_id: Optional[str] = None,
) -> AutoCritiqueResult:
    """Auto-critique a Designer proposal before human review.

    Does not replace human approval — it surfaces obvious issues early.
    """
    notes: List[CritiqueNote] = []
    verdict = "safe"
    safer_suggested = False

    node_count = len(nodes)

    # Overbuilt check
    if node_count > 10:
        notes.append(CritiqueNote(
            code="POTENTIALLY_OVERBUILT",
            message=f"circuit has {node_count} nodes; consider a simpler design",
        ))
        verdict = "overbuilt"
        safer_suggested = True

    # Invariant violations
    forbidden_kinds = [
        n.get("kind") for n in nodes if n.get("kind") in policy.forbidden_node_kinds
    ]
    if forbidden_kinds:
        notes.append(CritiqueNote(
            code="FORBIDDEN_NODE_KINDS_DETECTED",
            message=f"proposal contains forbidden node kinds: {forbidden_kinds}",
            severity="warning",
        ))
        verdict = "unsafe"

    # Missing output binding check
    output_bound = any(n.get("outputs") for n in nodes)
    if not output_bound:
        notes.append(CritiqueNote(
            code="NO_OUTPUT_BINDINGS",
            message="no node declares outputs; circuit may produce no usable result",
        ))

    # Check no prompt→provider→plugin forced pipeline ordering
    sequential_kinds = [n.get("kind") for n in nodes]
    if sequential_kinds == ["prompt", "provider", "plugin"]:
        notes.append(CritiqueNote(
            code="PIPELINE_COLLAPSE_RISK",
            message="node ordering matches forbidden pipeline pattern: prompt→provider→plugin",
            severity="warning",
        ))
        verdict = "unsafe"
        safer_suggested = True

    explanation = (
        f"auto-critique: {node_count} nodes; verdict={verdict}; "
        f"{len(notes)} note(s)"
    )

    return AutoCritiqueResult(
        critique_id=critique_id or str(uuid.uuid4()),
        overall_verdict=verdict,
        notes=notes,
        safer_alternative_suggested=safer_suggested,
        explanation=explanation,
    )
