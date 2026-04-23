"""test_step221_confidence_and_budget_routing.py

Tests for:
  - src/contracts/confidence_contract.py
  - src/engine/confidence_aggregator.py
  - src/contracts/budget_routing_contract.py
  - src/engine/budget_router.py
"""
from __future__ import annotations

import pytest

from src.contracts.confidence_contract import (
    BasisType,
    ConfidenceAssessment,
    ConfidenceBasis,
    ConfidenceContractError,
    RecommendedAction,
    ThresholdBand,
    ThresholdDecision,
    build_assessment,
    classify_confidence,
)
from src.engine.confidence_aggregator import (
    ConfidenceAggregatorError,
    aggregate_parallel_confidence,
    propagate_confidence,
)
from src.contracts.budget_routing_contract import (
    BudgetRoutingError,
    FallbackPlan,
    RouteDecision,
    RouteLog,
    RouteTier,
    RoutingContext,
    RiskLevel,
)
from src.engine.budget_router import decide_route, log_route


# ─────────────────────────────────────────────────────────────────────────────
# ConfidenceBasis contract
# ─────────────────────────────────────────────────────────────────────────────

class TestConfidenceBasis:
    def test_valid(self):
        b = ConfidenceBasis(
            basis_type=BasisType.EVIDENCE,
            source_ref="node:n1",
            contribution_weight=0.7,
        )
        assert b.basis_type == BasisType.EVIDENCE

    def test_invalid_basis_type(self):
        with pytest.raises(ConfidenceContractError):
            ConfidenceBasis(basis_type="magic", source_ref="x", contribution_weight=0.5)

    def test_weight_out_of_range(self):
        with pytest.raises(ConfidenceContractError):
            ConfidenceBasis(basis_type=BasisType.EVIDENCE, source_ref="x", contribution_weight=1.5)

    def test_empty_source_ref(self):
        with pytest.raises(ConfidenceContractError):
            ConfidenceBasis(basis_type=BasisType.VERIFIER, source_ref="", contribution_weight=0.5)

    def test_to_dict(self):
        b = ConfidenceBasis(BasisType.HISTORY, "src:1", 0.3, note="test")
        d = b.to_dict()
        assert d["basis_type"] == BasisType.HISTORY
        assert d["note"] == "test"


# ─────────────────────────────────────────────────────────────────────────────
# ThresholdDecision contract
# ─────────────────────────────────────────────────────────────────────────────

class TestThresholdDecision:
    def test_valid(self):
        td = ThresholdDecision(
            threshold_band=ThresholdBand.HIGH,
            recommended_action=RecommendedAction.CONTINUE,
            blocking=False,
        )
        assert not td.blocking

    def test_invalid_band(self):
        with pytest.raises(ConfidenceContractError):
            ThresholdDecision(threshold_band="ultra", recommended_action=RecommendedAction.CONTINUE, blocking=False)

    def test_invalid_action(self):
        with pytest.raises(ConfidenceContractError):
            ThresholdDecision(threshold_band=ThresholdBand.LOW, recommended_action="launch_missiles", blocking=True)

    def test_to_dict(self):
        td = ThresholdDecision(ThresholdBand.CRITICAL_LOW, RecommendedAction.HUMAN_REVIEW, True)
        d = td.to_dict()
        assert d["blocking"] is True


# ─────────────────────────────────────────────────────────────────────────────
# classify_confidence
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifyConfidence:
    def test_high(self):
        td = classify_confidence(0.9)
        assert td.threshold_band == ThresholdBand.HIGH
        assert td.recommended_action == RecommendedAction.CONTINUE
        assert not td.blocking

    def test_medium(self):
        td = classify_confidence(0.6)
        assert td.threshold_band == ThresholdBand.MEDIUM

    def test_low(self):
        td = classify_confidence(0.3)
        assert td.threshold_band == ThresholdBand.LOW

    def test_critical_low(self):
        td = classify_confidence(0.1)
        assert td.threshold_band == ThresholdBand.CRITICAL_LOW
        assert td.blocking is True

    def test_exact_boundary_high(self):
        td = classify_confidence(0.75)
        assert td.threshold_band == ThresholdBand.HIGH


# ─────────────────────────────────────────────────────────────────────────────
# build_assessment
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildAssessment:
    def test_basic(self):
        a = build_assessment(target_ref="node:n1", confidence_score=0.8)
        assert a.confidence_score == 0.8
        assert a.uncertainty_score == pytest.approx(0.2)
        assert a.threshold_decision.threshold_band == ThresholdBand.HIGH

    def test_explicit_uncertainty(self):
        a = build_assessment(
            target_ref="node:n2", confidence_score=0.6, uncertainty_score=0.3
        )
        assert a.uncertainty_score == 0.3

    def test_to_dict_roundtrip(self):
        a = build_assessment(target_ref="n1", confidence_score=0.5)
        d = a.to_dict()
        a2 = ConfidenceAssessment.from_dict(d)
        assert a2.confidence_score == a.confidence_score
        assert a2.target_ref == a.target_ref

    def test_invalid_scores_rejected(self):
        with pytest.raises(ConfidenceContractError):
            build_assessment(target_ref="x", confidence_score=1.5)


# ─────────────────────────────────────────────────────────────────────────────
# propagate_confidence
# ─────────────────────────────────────────────────────────────────────────────

class TestPropagateConfidence:
    def test_no_upstream(self):
        result = propagate_confidence(
            upstream_assessments=[],
            local_evidence_density=0.6,
            target_ref="node:out",
        )
        assert result.confidence_score == pytest.approx(0.6)

    def test_low_upstream_floor(self):
        up = build_assessment(target_ref="u1", confidence_score=0.2)
        result = propagate_confidence(
            upstream_assessments=[up],
            local_evidence_density=0.9,
            target_ref="node:out",
        )
        # confidence cannot silently jump to high; capped by evidence ceiling
        assert result.confidence_score <= 0.9
        # Upstream floor dominates
        assert result.confidence_score <= 0.55  # floor=0.2, boost=0, ceiling=0.7

    def test_verifier_boost_capped(self):
        up = build_assessment(target_ref="u1", confidence_score=0.5)
        result = propagate_confidence(
            upstream_assessments=[up],
            local_evidence_density=0.8,
            verifier_boost=0.5,  # should be capped at 0.2
            target_ref="node:out",
        )
        # boost capped at 0.2; max recovery = 0.5 + 0.2 = 0.7
        assert result.confidence_score <= 0.75

    def test_basis_records_upstream(self):
        up = build_assessment(target_ref="u1", confidence_score=0.7)
        result = propagate_confidence(
            upstream_assessments=[up],
            target_ref="node:out",
        )
        assert len(result.confidence_basis) == 1
        assert result.confidence_basis[0].basis_type == BasisType.HISTORY


# ─────────────────────────────────────────────────────────────────────────────
# aggregate_parallel_confidence
# ─────────────────────────────────────────────────────────────────────────────

class TestAggregateParallelConfidence:
    def _make(self, score: float) -> ConfidenceAssessment:
        return build_assessment(target_ref="branch", confidence_score=score)

    def test_min_strategy(self):
        assessments = [self._make(0.9), self._make(0.4)]
        r = aggregate_parallel_confidence(assessments, target_ref="merge", strategy="min")
        assert r.confidence_score <= 0.4

    def test_mean_strategy(self):
        assessments = [self._make(0.8), self._make(0.6)]
        r = aggregate_parallel_confidence(assessments, target_ref="merge", strategy="mean")
        assert 0.6 <= r.confidence_score <= 0.8

    def test_max_strategy(self):
        assessments = [self._make(0.3), self._make(0.9)]
        r = aggregate_parallel_confidence(assessments, target_ref="merge", strategy="max")
        assert r.confidence_score == pytest.approx(0.9)

    def test_disagreement_lowers_min(self):
        assessments = [self._make(0.9), self._make(0.1)]
        r = aggregate_parallel_confidence(assessments, target_ref="merge", strategy="min")
        # spread=0.8 > 0.3 → penalty 0.1 on top of min 0.1
        assert r.confidence_score <= 0.1  # already 0.1, penalty = max(0, 0.1-0.1)=0

    def test_empty_raises(self):
        with pytest.raises(ConfidenceAggregatorError):
            aggregate_parallel_confidence([], target_ref="merge")

    def test_agreement_score_reflects_spread(self):
        assessments = [self._make(0.9), self._make(0.1)]
        r = aggregate_parallel_confidence(assessments, target_ref="merge", strategy="mean")
        assert r.agreement_score is not None
        assert r.agreement_score < 0.5  # high spread → low agreement


# ─────────────────────────────────────────────────────────────────────────────
# RoutingContext contract
# ─────────────────────────────────────────────────────────────────────────────

class TestRoutingContext:
    def _ctx(self, **kwargs):
        defaults = dict(
            node_id="n1",
            task_type="summarize",
            current_budget=10.0,
            difficulty_estimate=0.5,
            risk_level=RiskLevel.LOW,
            allowed_providers=["gpt4"],
        )
        defaults.update(kwargs)
        return RoutingContext(**defaults)

    def test_valid(self):
        ctx = self._ctx()
        assert ctx.node_id == "n1"

    def test_empty_node_id(self):
        with pytest.raises(BudgetRoutingError):
            self._ctx(node_id="")

    def test_negative_budget(self):
        with pytest.raises(BudgetRoutingError):
            self._ctx(current_budget=-1)

    def test_invalid_risk_level(self):
        with pytest.raises(BudgetRoutingError):
            self._ctx(risk_level="extreme")

    def test_to_dict(self):
        ctx = self._ctx()
        d = ctx.to_dict()
        assert d["node_id"] == "n1"


# ─────────────────────────────────────────────────────────────────────────────
# decide_route
# ─────────────────────────────────────────────────────────────────────────────

class TestDecideRoute:
    def _ctx(self, **kwargs):
        defaults = dict(
            node_id="n1",
            task_type="write",
            current_budget=50.0,
            difficulty_estimate=0.3,
            risk_level=RiskLevel.LOW,
            allowed_providers=["gpt4", "claude"],
        )
        defaults.update(kwargs)
        return RoutingContext(**defaults)

    def test_low_risk_standard_gets_balanced(self):
        ctx = self._ctx()
        d = decide_route(ctx)
        assert d.selected_route_tier == RouteTier.BALANCED

    def test_high_difficulty_gets_high_quality(self):
        ctx = self._ctx(difficulty_estimate=0.9)
        d = decide_route(ctx)
        assert d.selected_route_tier == RouteTier.HIGH_QUALITY

    def test_restricted_risk_gets_high_safety(self):
        ctx = self._ctx(risk_level=RiskLevel.RESTRICTED)
        d = decide_route(ctx)
        assert d.selected_route_tier == RouteTier.HIGH_SAFETY

    def test_retry_escalates(self):
        ctx = self._ctx(retry_count=1)
        d = decide_route(ctx)
        # BALANCED escalates to HIGH_QUALITY
        assert d.selected_route_tier in (RouteTier.HIGH_QUALITY, RouteTier.HIGH_SAFETY)

    def test_no_providers_raises(self):
        ctx = self._ctx(allowed_providers=[])
        with pytest.raises(BudgetRoutingError):
            decide_route(ctx)

    def test_budget_exhausted_still_produces_decision(self):
        ctx = self._ctx(current_budget=0.0)
        d = decide_route(ctx)
        assert d.selected_route_tier == RouteTier.CHEAP
        assert "BUDGET_EXHAUSTED" in d.selection_reason_codes

    def test_fallback_armed_for_cheap(self):
        ctx = self._ctx(current_budget=0.5)
        d = decide_route(ctx)
        assert d.fallback_plan.enabled is True

    def test_route_decision_immutable(self):
        ctx = self._ctx()
        d = decide_route(ctx)
        with pytest.raises(Exception):
            d.route_id = "hack"  # type: ignore[misc]

    def test_to_dict_complete(self):
        ctx = self._ctx()
        d = decide_route(ctx)
        di = d.to_dict()
        assert "route_id" in di
        assert "fallback_plan" in di

    def test_quality_target_high_selects_high_quality(self):
        ctx = self._ctx(quality_target=0.9)
        d = decide_route(ctx)
        assert d.selected_route_tier == RouteTier.HIGH_QUALITY


# ─────────────────────────────────────────────────────────────────────────────
# log_route
# ─────────────────────────────────────────────────────────────────────────────

class TestLogRoute:
    def test_basic(self):
        ctx = RoutingContext(
            node_id="n1", task_type="t", current_budget=10.0,
            difficulty_estimate=0.3, risk_level=RiskLevel.LOW,
            allowed_providers=["p1"],
        )
        d = decide_route(ctx)
        log = log_route(d, ctx)
        assert log.verifier_contradicted is False
        assert log.route_decision is d

    def test_verifier_contradiction_flag(self):
        ctx = RoutingContext(
            node_id="n1", task_type="t", current_budget=10.0,
            difficulty_estimate=0.3, risk_level=RiskLevel.LOW,
            allowed_providers=["p1"],
        )
        d = decide_route(ctx)
        log = log_route(d, ctx, verifier_contradicted=True, notes="verifier said fail")
        assert log.verifier_contradicted is True

    def test_to_dict(self):
        ctx = RoutingContext(
            node_id="n1", task_type="t", current_budget=10.0,
            difficulty_estimate=0.3, risk_level=RiskLevel.LOW,
            allowed_providers=["p1"],
        )
        d = decide_route(ctx)
        log = log_route(d, ctx)
        di = log.to_dict()
        assert "log_id" in di
        assert "routing_context" in di
