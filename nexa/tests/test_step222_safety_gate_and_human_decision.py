"""test_step222_safety_gate_and_human_decision.py

Tests for:
  - src/contracts/safety_gate_contract.py
  - src/engine/safety_gate.py
  - src/contracts/human_decision_contract.py
  - src/engine/human_decision_registry.py
"""
from __future__ import annotations

import pytest

from src.contracts.safety_gate_contract import (
    GateStatus,
    PermissionSet,
    RiskTier,
    SafetyGateError,
    SafetyGateResult,
)
from src.engine.safety_gate import (
    classify_risk,
    evaluate_gate,
)
from src.contracts.human_decision_contract import (
    DownstreamAction,
    HumanDecisionError,
    HumanDecisionRecord,
    HumanDecisionType,
    record_human_decision,
)
from src.engine.human_decision_registry import HumanDecisionRegistry


# ─────────────────────────────────────────────────────────────────────────────
# SafetyGateResult contract
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyGateResult:
    def _make(self, **kw):
        defaults = dict(
            gate_id="g1",
            target_ref="node:n1",
            risk_tier=RiskTier.LOW,
            status=GateStatus.ALLOW,
            reason_codes=["OK"],
            blocked_actions=[],
            allowed_actions=["read"],
            required_reviews=[],
            explanation="ok",
        )
        defaults.update(kw)
        return SafetyGateResult(**defaults)

    def test_valid(self):
        r = self._make()
        assert not r.is_blocked
        assert not r.requires_review

    def test_blocked_is_blocked(self):
        r = self._make(status=GateStatus.BLOCK, risk_tier=RiskTier.BLOCKED)
        assert r.is_blocked

    def test_restrict_requires_review(self):
        r = self._make(status=GateStatus.RESTRICT, risk_tier=RiskTier.RESTRICTED)
        assert r.requires_review

    def test_invalid_risk_tier(self):
        with pytest.raises(SafetyGateError):
            self._make(risk_tier="fantasy")

    def test_invalid_status(self):
        with pytest.raises(SafetyGateError):
            self._make(status="maybe")

    def test_empty_gate_id(self):
        with pytest.raises(SafetyGateError):
            self._make(gate_id="")

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert d["risk_tier"] == RiskTier.LOW
        assert "blocked_actions" in d


# ─────────────────────────────────────────────────────────────────────────────
# classify_risk
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyRisk:
    def test_safe_actions(self):
        tier = classify_risk(requested_actions=["read", "summarize"])
        assert tier == RiskTier.LOW

    def test_blocked_action_immediately_blocked(self):
        tier = classify_risk(requested_actions=["delete_all"])
        assert tier == RiskTier.BLOCKED

    def test_restricted_action_escalates(self):
        tier = classify_risk(requested_actions=["file_mutation"])
        assert tier == RiskTier.RESTRICTED

    def test_data_sensitivity_baseline(self):
        tier = classify_risk(
            requested_actions=["read"],
            data_sensitivity=RiskTier.HIGH,
        )
        assert tier == RiskTier.HIGH

    def test_policy_override_applied(self):
        tier = classify_risk(
            requested_actions=["custom_action"],
            policy_overrides={"custom_action": RiskTier.HIGH},
        )
        assert tier == RiskTier.HIGH

    def test_multiple_actions_worst_case(self):
        tier = classify_risk(requested_actions=["read", "file_mutation"])
        assert tier == RiskTier.RESTRICTED


# ─────────────────────────────────────────────────────────────────────────────
# evaluate_gate
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluateGate:
    def test_safe_actions_allowed(self):
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["read", "summarize"],
        )
        assert result.status == GateStatus.ALLOW
        assert not result.is_blocked

    def test_blocked_action_produces_block(self):
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["delete_all"],
        )
        assert result.is_blocked
        assert "delete_all" in result.blocked_actions

    def test_permission_set_denied_action(self):
        ps = PermissionSet(denied_actions=["write"])
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["write"],
            permission_set=ps,
        )
        assert result.is_blocked
        assert "write" in result.blocked_actions

    def test_permission_allowlist_rejects_unlisted(self):
        ps = PermissionSet(allowed_actions=["read"])
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["read", "write"],
            permission_set=ps,
        )
        assert "write" in result.blocked_actions

    def test_human_approval_required_by_permission_set(self):
        ps = PermissionSet(requires_human_approval=True)
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["safe_action"],
            permission_set=ps,
        )
        assert result.requires_review
        assert "human_approval" in result.required_reviews

    def test_restricted_action_gets_restrict_status(self):
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["external_api_call"],
        )
        assert result.status in (GateStatus.RESTRICT, GateStatus.BLOCK)

    def test_denied_provider_escalates(self):
        ps = PermissionSet(denied_providers=["bad_provider"])
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["read"],
            permission_set=ps,
            requested_providers=["bad_provider"],
        )
        assert any("PROVIDER_DENIED" in rc for rc in result.reason_codes)

    def test_to_dict_complete(self):
        result = evaluate_gate(target_ref="node:n1", requested_actions=["read"])
        d = result.to_dict()
        assert "gate_id" in d
        assert "risk_tier" in d

    def test_mixed_safe_and_blocked(self):
        result = evaluate_gate(
            target_ref="node:n1",
            requested_actions=["read", "bypass_human_approval"],
        )
        assert result.is_blocked
        assert "bypass_human_approval" in result.blocked_actions
        assert "read" in result.allowed_actions


# ─────────────────────────────────────────────────────────────────────────────
# HumanDecisionRecord contract
# ─────────────────────────────────────────────────────────────────────────────

class TestHumanDecisionRecord:
    def _make(self, **kw):
        defaults = dict(
            decision_id="d1",
            target_ref="node:review",
            decision_type=HumanDecisionType.APPROVE,
            actor_ref="user:alice",
            downstream_action=DownstreamAction.CONTINUE,
            trace_refs=["trace:t1"],
            timestamp="2025-01-01T00:00:00Z",
        )
        defaults.update(kw)
        return HumanDecisionRecord(**defaults)

    def test_valid(self):
        r = self._make()
        assert r.decision_type == HumanDecisionType.APPROVE

    def test_empty_actor_ref_rejected(self):
        """No silent auto-approval: actor_ref must be non-empty."""
        with pytest.raises(HumanDecisionError, match="actor_ref"):
            self._make(actor_ref="")

    def test_invalid_decision_type(self):
        with pytest.raises(HumanDecisionError):
            self._make(decision_type="teleport")

    def test_invalid_downstream_action(self):
        with pytest.raises(HumanDecisionError):
            self._make(downstream_action="vanish")

    def test_empty_target_ref(self):
        with pytest.raises(HumanDecisionError):
            self._make(target_ref="")

    def test_to_dict(self):
        r = self._make()
        d = r.to_dict()
        assert d["actor_ref"] == "user:alice"
        assert "trace_refs" in d

    def test_from_dict_roundtrip(self):
        r = self._make()
        d = r.to_dict()
        r2 = HumanDecisionRecord.from_dict(d)
        assert r2.decision_id == r.decision_id
        assert r2.actor_ref == r.actor_ref

    def test_all_decision_types_valid(self):
        for dt in HumanDecisionType._ALL:
            r = record_human_decision(
                target_ref="n1",
                decision_type=dt,
                actor_ref="user:bob",
                downstream_action=DownstreamAction.CONTINUE,
            )
            assert r.decision_type == dt


# ─────────────────────────────────────────────────────────────────────────────
# record_human_decision factory
# ─────────────────────────────────────────────────────────────────────────────

class TestRecordHumanDecision:
    def test_produces_record(self):
        r = record_human_decision(
            target_ref="node:rev",
            decision_type=HumanDecisionType.REJECT,
            actor_ref="user:bob",
            downstream_action=DownstreamAction.STOP,
            rationale_text="quality too low",
        )
        assert r.rationale_text == "quality too low"
        assert r.decision_id  # non-empty auto-generated

    def test_custom_decision_id(self):
        r = record_human_decision(
            target_ref="n",
            decision_type=HumanDecisionType.APPROVE,
            actor_ref="u",
            downstream_action=DownstreamAction.CONTINUE,
            decision_id="fixed-id",
        )
        assert r.decision_id == "fixed-id"


# ─────────────────────────────────────────────────────────────────────────────
# HumanDecisionRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestHumanDecisionRegistry:
    def _record(self, target="n1", dt=HumanDecisionType.APPROVE, action=DownstreamAction.CONTINUE):
        return record_human_decision(
            target_ref=target,
            decision_type=dt,
            actor_ref="user:alice",
            downstream_action=action,
        )

    def test_register_and_get(self):
        reg = HumanDecisionRegistry()
        r = self._record()
        reg.register(r)
        assert reg.get(r.decision_id) is r

    def test_duplicate_raises(self):
        reg = HumanDecisionRegistry()
        r = self._record()
        reg.register(r)
        with pytest.raises(HumanDecisionError):
            reg.register(r)

    def test_by_target(self):
        reg = HumanDecisionRegistry()
        r1 = self._record(target="n1")
        r2 = self._record(target="n2")
        reg.register(r1)
        reg.register(r2)
        assert reg.by_target("n1") == [r1]

    def test_by_type(self):
        reg = HumanDecisionRegistry()
        r1 = self._record(dt=HumanDecisionType.APPROVE)
        r2 = self._record(dt=HumanDecisionType.REJECT)
        reg.register(r1)
        reg.register(r2)
        assert reg.by_type(HumanDecisionType.REJECT) == [r2]

    def test_pending_reviews(self):
        reg = HumanDecisionRegistry()
        r1 = self._record(action=DownstreamAction.ESCALATE)
        r2 = self._record(action=DownstreamAction.CONTINUE)
        reg.register(r1)
        reg.register(r2)
        pending = reg.pending_reviews()
        assert r1 in pending
        assert r2 not in pending

    def test_count(self):
        reg = HumanDecisionRegistry()
        reg.register(self._record())
        reg.register(self._record())
        assert reg.count() == 2

    def test_all_records(self):
        reg = HumanDecisionRegistry()
        reg.register(self._record())
        assert len(reg.all_records()) == 1
