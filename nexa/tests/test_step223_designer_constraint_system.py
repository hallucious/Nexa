"""test_step223_designer_constraint_system.py

Tests for:
  - src/designer/designer_constraint_system.py
"""
from __future__ import annotations

import pytest

from src.designer.designer_constraint_system import (
    DEFAULT_CONSTRAINT_POLICY,
    AutoCritiqueResult,
    CircuitLintResult,
    DesignerConstraintError,
    DesignerConstraintPolicy,
    LintViolation,
    critique_proposal,
    lint_circuit_proposal,
)


# ─────────────────────────────────────────────────────────────────────────────
# DesignerConstraintPolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestDesignerConstraintPolicy:
    def test_default_policy_valid(self):
        p = DEFAULT_CONSTRAINT_POLICY
        assert p.policy_id == "default"
        assert "execution" in p.allowed_node_kinds

    def test_empty_policy_id_rejected(self):
        with pytest.raises(DesignerConstraintError):
            DesignerConstraintPolicy(
                policy_id="",
                allowed_node_kinds=["execution"],
                allowed_resource_types=["prompt"],
            )

    def test_to_dict(self):
        d = DEFAULT_CONSTRAINT_POLICY.to_dict()
        assert "policy_id" in d
        assert "allowed_node_kinds" in d
        assert "forbidden_node_kinds" in d


# ─────────────────────────────────────────────────────────────────────────────
# lint_circuit_proposal
# ─────────────────────────────────────────────────────────────────────────────

class TestLintCircuitProposal:
    def _node(self, node_id="n1", kind="execution", resources=None, **kw):
        return {"id": node_id, "kind": kind, "resources": resources or [], **kw}

    def test_empty_circuit_passes(self):
        result = lint_circuit_proposal(nodes=[])
        assert result.passed

    def test_valid_node_passes(self):
        nodes = [self._node(outputs=["out1"])]
        result = lint_circuit_proposal(nodes=nodes)
        assert result.passed

    def test_forbidden_node_kind_fails(self):
        nodes = [self._node(kind="pipeline_step", outputs=["o"])]
        result = lint_circuit_proposal(nodes=nodes)
        assert not result.passed
        codes = [v.code for v in result.violations]
        assert "FORBIDDEN_NODE_KIND" in codes

    def test_dead_end_node_warning(self):
        nodes = [self._node()]  # no outputs
        result = lint_circuit_proposal(nodes=nodes)
        warning_codes = [w.code for w in result.warnings]
        assert "DEAD_END_NODE" in warning_codes

    def test_forbidden_resource_pattern_fails(self):
        nodes = [self._node(resources=["plugin.unrestricted_write.x"], outputs=["o"])]
        result = lint_circuit_proposal(nodes=nodes)
        assert not result.passed
        codes = [v.code for v in result.violations]
        assert "FORBIDDEN_RESOURCE_PATTERN" in codes

    def test_high_risk_missing_verifier_fails(self):
        nodes = [
            self._node(risk_level="high", outputs=["o"]),
        ]
        result = lint_circuit_proposal(nodes=nodes)
        assert not result.passed
        codes = [v.code for v in result.violations]
        assert "HIGH_RISK_MISSING_VERIFIER" in codes

    def test_high_risk_with_verifier_passes(self):
        nodes = [
            self._node("n1", risk_level="high", resources=["verifier"], outputs=["o"]),
            self._node("n2", kind="verification", resources=["verifier"], outputs=["o"]),
        ]
        result = lint_circuit_proposal(nodes=nodes)
        # Should not fail on HIGH_RISK_MISSING_VERIFIER
        codes = [v.code for v in result.violations]
        assert "HIGH_RISK_MISSING_VERIFIER" not in codes

    def test_too_many_nodes_fails(self):
        nodes = [self._node(f"n{i}", outputs=["o"]) for i in range(51)]
        result = lint_circuit_proposal(nodes=nodes)
        assert not result.passed
        codes = [v.code for v in result.violations]
        assert "CIRCUIT_TOO_LARGE" in codes

    def test_lint_id_generated(self):
        result = lint_circuit_proposal(nodes=[])
        assert result.lint_id

    def test_to_dict(self):
        result = lint_circuit_proposal(nodes=[self._node(outputs=["o"])])
        d = result.to_dict()
        assert "lint_id" in d
        assert "violations" in d
        assert "warnings" in d

    def test_violation_has_node_ref(self):
        nodes = [self._node(kind="pipeline_step", outputs=["o"])]
        result = lint_circuit_proposal(nodes=nodes)
        violation = result.violations[0]
        assert violation.node_ref == "n1"

    def test_unknown_node_kind_is_warning_not_violation(self):
        nodes = [self._node(kind="exotic_kind", outputs=["o"])]
        result = lint_circuit_proposal(nodes=nodes)
        warning_codes = [w.code for w in result.warnings]
        assert "UNKNOWN_NODE_KIND" in warning_codes
        # Should still pass (only warning)
        assert result.passed


# ─────────────────────────────────────────────────────────────────────────────
# critique_proposal
# ─────────────────────────────────────────────────────────────────────────────

class TestCritiqueProposal:
    def _node(self, node_id="n1", kind="execution", outputs=None):
        return {"id": node_id, "kind": kind, "outputs": outputs or ["out"]}

    def test_small_valid_circuit_is_safe(self):
        nodes = [self._node()]
        result = critique_proposal(nodes=nodes, user_request_summary="summarize text")
        assert result.overall_verdict == "safe"
        assert not result.safer_alternative_suggested

    def test_large_circuit_is_overbuilt(self):
        nodes = [self._node(f"n{i}") for i in range(12)]
        result = critique_proposal(nodes=nodes)
        assert result.overall_verdict == "overbuilt"
        assert result.safer_alternative_suggested

    def test_forbidden_node_kind_makes_unsafe(self):
        nodes = [{"id": "n1", "kind": "pipeline_step", "outputs": ["o"]}]
        result = critique_proposal(nodes=nodes)
        assert result.overall_verdict == "unsafe"

    def test_pipeline_collapse_detected(self):
        nodes = [
            {"id": "n1", "kind": "prompt", "outputs": ["o"]},
            {"id": "n2", "kind": "provider", "outputs": ["o"]},
            {"id": "n3", "kind": "plugin", "outputs": ["o"]},
        ]
        result = critique_proposal(nodes=nodes)
        codes = [n.code for n in result.notes]
        assert "PIPELINE_COLLAPSE_RISK" in codes
        assert result.overall_verdict == "unsafe"

    def test_no_output_bindings_noted(self):
        nodes = [{"id": "n1", "kind": "execution"}]
        result = critique_proposal(nodes=nodes)
        codes = [n.code for n in result.notes]
        assert "NO_OUTPUT_BINDINGS" in codes

    def test_critique_id_generated(self):
        result = critique_proposal(nodes=[self._node()])
        assert result.critique_id

    def test_to_dict(self):
        result = critique_proposal(nodes=[self._node()])
        d = result.to_dict()
        assert "critique_id" in d
        assert "overall_verdict" in d
        assert "notes" in d
