"""
test_execution_regression_policy.py

Tests for execution_regression_policy module.

Coverage:
1.  No regressions → PASS
2.  Only LOW regressions → PASS
3.  MEDIUM regressions → WARN
4.  HIGH regressions → FAIL
5.  Mixed severities → FAIL dominates
6.  Determinism (same input → same output)
7.  PolicyDecision validation
8.  FAIL reasons: summary line + trigger lines
9.  WARN reasons: summary line + trigger lines
10. PASS reason: single informational line
11. Trigger line content correctness (node / artifact / context)
12. Reason ordering: nodes → artifacts → context
13. No mutation of input
"""
import pytest

from src.engine.execution_regression_detector import (
    ArtifactRegression,
    ContextRegression,
    NodeRegression,
    RegressionResult,
    RegressionSummary,
)
from src.contracts.regression_reason_codes import (
    ARTIFACT_HASH_CHANGED,
    ARTIFACT_REMOVED,
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
)
from src.engine.execution_regression_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_PASS,
    POLICY_STATUS_WARN,
    PolicyDecision,
    evaluate_regression_policy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_result() -> RegressionResult:
    return RegressionResult(status="clean")


def _result_with_nodes(*nodes: NodeRegression) -> RegressionResult:
    return RegressionResult(status="regression", nodes=list(nodes))


def _result_with_artifacts(*artifacts: ArtifactRegression) -> RegressionResult:
    return RegressionResult(status="regression", artifacts=list(artifacts))


def _result_with_context(*context: ContextRegression) -> RegressionResult:
    return RegressionResult(status="regression", context=list(context))


def _high_node(node_id: str = "node_a") -> NodeRegression:
    return NodeRegression(
        node_id=node_id,
        reason_code=NODE_SUCCESS_TO_FAILURE,
        left_status="success",
        right_status="failure",
    )


def _medium_node(node_id: str = "node_b") -> NodeRegression:
    return NodeRegression(
        node_id=node_id,
        reason_code=NODE_SUCCESS_TO_SKIPPED,
        left_status="success",
        right_status="skipped",
    )


def _low_context(key: str = "output.value") -> ContextRegression:
    return ContextRegression(
        context_key=key,
        reason_code=CONTEXT_VALUE_CHANGED,
    )


def _medium_artifact(artifact_id: str = "art_1") -> ArtifactRegression:
    return ArtifactRegression(
        artifact_id=artifact_id,
        reason_code=ARTIFACT_HASH_CHANGED,
    )


def _high_artifact(artifact_id: str = "art_2") -> ArtifactRegression:
    return ArtifactRegression(
        artifact_id=artifact_id,
        reason_code=ARTIFACT_REMOVED,
    )


def _medium_context(key: str = "ctx.key") -> ContextRegression:
    return ContextRegression(
        context_key=key,
        reason_code=CONTEXT_KEY_REMOVED,
    )


# ---------------------------------------------------------------------------
# 1. No regressions → PASS
# ---------------------------------------------------------------------------

def test_no_regressions_returns_pass():
    assert evaluate_regression_policy(_clean_result()).status == POLICY_STATUS_PASS


def test_no_regressions_has_one_reason():
    decision = evaluate_regression_policy(_clean_result())
    assert len(decision.reasons) == 1


def test_no_regressions_reason_starts_with_pass():
    decision = evaluate_regression_policy(_clean_result())
    assert decision.reasons[0].startswith("PASS:")


# ---------------------------------------------------------------------------
# 2. Only LOW regressions → PASS
# ---------------------------------------------------------------------------

def test_only_low_regressions_returns_pass():
    decision = evaluate_regression_policy(_result_with_context(_low_context()))
    assert decision.status == POLICY_STATUS_PASS


def test_only_low_regressions_reason_starts_with_pass():
    decision = evaluate_regression_policy(_result_with_context(_low_context()))
    assert decision.reasons[0].startswith("PASS:")


def test_multiple_low_regressions_returns_pass():
    result = _result_with_context(_low_context("output.x"), _low_context("output.y"))
    assert evaluate_regression_policy(result).status == POLICY_STATUS_PASS


# ---------------------------------------------------------------------------
# 3. MEDIUM regressions → WARN
# ---------------------------------------------------------------------------

def test_medium_node_regression_returns_warn():
    assert evaluate_regression_policy(_result_with_nodes(_medium_node())).status == POLICY_STATUS_WARN


def test_medium_artifact_regression_returns_warn():
    assert evaluate_regression_policy(_result_with_artifacts(_medium_artifact())).status == POLICY_STATUS_WARN


def test_medium_context_regression_returns_warn():
    assert evaluate_regression_policy(_result_with_context(_medium_context())).status == POLICY_STATUS_WARN


def test_medium_regression_summary_line_format():
    decision = evaluate_regression_policy(_result_with_nodes(_medium_node()))
    assert decision.reasons[0].startswith("WARN:")
    assert "medium" in decision.reasons[0].lower()
    assert "1" in decision.reasons[0]


def test_medium_regression_has_trigger_line():
    decision = evaluate_regression_policy(_result_with_nodes(_medium_node()))
    assert len(decision.reasons) == 2
    assert decision.reasons[1].startswith("Trigger:")


def test_medium_node_trigger_line_content():
    decision = evaluate_regression_policy(_result_with_nodes(_medium_node("n_test")))
    trigger = decision.reasons[1]
    assert "n_test" in trigger
    assert NODE_SUCCESS_TO_SKIPPED in trigger
    assert "MEDIUM" in trigger


def test_medium_artifact_trigger_line_content():
    decision = evaluate_regression_policy(_result_with_artifacts(_medium_artifact("a_test")))
    trigger = decision.reasons[1]
    assert "a_test" in trigger
    assert ARTIFACT_HASH_CHANGED in trigger
    assert "MEDIUM" in trigger


def test_medium_context_trigger_line_content():
    decision = evaluate_regression_policy(_result_with_context(_medium_context("c.test")))
    trigger = decision.reasons[1]
    assert "c.test" in trigger
    assert CONTEXT_KEY_REMOVED in trigger
    assert "MEDIUM" in trigger


# ---------------------------------------------------------------------------
# 4. HIGH regressions → FAIL
# ---------------------------------------------------------------------------

def test_high_node_regression_returns_fail():
    assert evaluate_regression_policy(_result_with_nodes(_high_node())).status == POLICY_STATUS_FAIL


def test_high_artifact_regression_returns_fail():
    assert evaluate_regression_policy(_result_with_artifacts(_high_artifact())).status == POLICY_STATUS_FAIL


def test_high_regression_summary_line_format():
    decision = evaluate_regression_policy(_result_with_nodes(_high_node()))
    assert decision.reasons[0].startswith("FAIL:")
    assert "high" in decision.reasons[0].lower()
    assert "1" in decision.reasons[0]


def test_high_regression_has_trigger_line():
    decision = evaluate_regression_policy(_result_with_nodes(_high_node()))
    assert len(decision.reasons) == 2
    assert decision.reasons[1].startswith("Trigger:")


def test_high_node_trigger_line_content():
    decision = evaluate_regression_policy(_result_with_nodes(_high_node("n_fail")))
    trigger = decision.reasons[1]
    assert "n_fail" in trigger
    assert NODE_SUCCESS_TO_FAILURE in trigger
    assert "HIGH" in trigger


def test_high_artifact_trigger_line_content():
    decision = evaluate_regression_policy(_result_with_artifacts(_high_artifact("a_fail")))
    trigger = decision.reasons[1]
    assert "a_fail" in trigger
    assert ARTIFACT_REMOVED in trigger
    assert "HIGH" in trigger


# ---------------------------------------------------------------------------
# 5. Mixed severities → FAIL dominates
# ---------------------------------------------------------------------------

def test_high_and_medium_returns_fail():
    result = RegressionResult(status="regression", nodes=[_high_node(), _medium_node()])
    assert evaluate_regression_policy(result).status == POLICY_STATUS_FAIL


def test_high_and_low_returns_fail():
    result = RegressionResult(status="regression", nodes=[_high_node()], context=[_low_context()])
    assert evaluate_regression_policy(result).status == POLICY_STATUS_FAIL


def test_medium_and_low_returns_warn():
    result = RegressionResult(status="regression", nodes=[_medium_node()], context=[_low_context()])
    assert evaluate_regression_policy(result).status == POLICY_STATUS_WARN


def test_all_severities_returns_fail():
    result = RegressionResult(
        status="regression",
        nodes=[_high_node(), _medium_node()],
        context=[_low_context()],
    )
    assert evaluate_regression_policy(result).status == POLICY_STATUS_FAIL


def test_mixed_fail_reasons_only_include_high_triggers():
    """FAIL reasons must only list HIGH triggers, not MEDIUM or LOW."""
    result = RegressionResult(
        status="regression",
        nodes=[_high_node("h1"), _medium_node("m1")],
        context=[_low_context()],
    )
    decision = evaluate_regression_policy(result)
    assert decision.status == POLICY_STATUS_FAIL
    triggers = [r for r in decision.reasons if r.startswith("Trigger:")]
    assert len(triggers) == 1
    assert "h1" in triggers[0]
    assert "m1" not in triggers[0]


def test_multiple_high_triggers_all_listed():
    result = RegressionResult(status="regression", nodes=[_high_node("h1"), _high_node("h2")])
    decision = evaluate_regression_policy(result)
    triggers = [r for r in decision.reasons if r.startswith("Trigger:")]
    assert len(triggers) == 2
    combined = " ".join(triggers)
    assert "h1" in combined
    assert "h2" in combined


def test_multiple_medium_triggers_all_listed():
    result = RegressionResult(status="regression", nodes=[_medium_node("m1"), _medium_node("m2")])
    decision = evaluate_regression_policy(result)
    triggers = [r for r in decision.reasons if r.startswith("Trigger:")]
    assert len(triggers) == 2


# ---------------------------------------------------------------------------
# 6. Trigger ordering: nodes → artifacts → context
# ---------------------------------------------------------------------------

def test_trigger_ordering_nodes_before_artifacts():
    result = RegressionResult(
        status="regression",
        nodes=[_high_node("n1")],
        artifacts=[_high_artifact("a1")],
    )
    triggers = [r for r in evaluate_regression_policy(result).reasons if r.startswith("Trigger:")]
    assert len(triggers) == 2
    assert "n1" in triggers[0]
    assert "a1" in triggers[1]


def test_trigger_ordering_artifacts_before_context():
    result = RegressionResult(
        status="regression",
        artifacts=[_medium_artifact("a1")],
        context=[_medium_context("c1")],
    )
    triggers = [r for r in evaluate_regression_policy(result).reasons if r.startswith("Trigger:")]
    assert len(triggers) == 2
    assert "a1" in triggers[0]
    assert "c1" in triggers[1]


def test_trigger_ordering_nodes_before_context():
    result = RegressionResult(
        status="regression",
        nodes=[_medium_node("n1")],
        context=[_medium_context("c1")],
    )
    triggers = [r for r in evaluate_regression_policy(result).reasons if r.startswith("Trigger:")]
    assert len(triggers) == 2
    assert "n1" in triggers[0]
    assert "c1" in triggers[1]


def test_trigger_input_order_preserved_within_category():
    result = RegressionResult(
        status="regression",
        nodes=[_high_node("n1"), _high_node("n2"), _high_node("n3")],
    )
    triggers = [r for r in evaluate_regression_policy(result).reasons if r.startswith("Trigger:")]
    assert "n1" in triggers[0]
    assert "n2" in triggers[1]
    assert "n3" in triggers[2]


# ---------------------------------------------------------------------------
# 7. Determinism
# ---------------------------------------------------------------------------

def test_determinism_clean():
    result = _clean_result()
    d1 = evaluate_regression_policy(result)
    d2 = evaluate_regression_policy(result)
    assert d1.status == d2.status
    assert d1.reasons == d2.reasons


def test_determinism_high():
    result = _result_with_nodes(_high_node())
    d1 = evaluate_regression_policy(result)
    d2 = evaluate_regression_policy(result)
    assert d1.status == d2.status
    assert d1.reasons == d2.reasons


def test_determinism_medium():
    result = _result_with_nodes(_medium_node())
    d1 = evaluate_regression_policy(result)
    d2 = evaluate_regression_policy(result)
    assert d1.status == d2.status
    assert d1.reasons == d2.reasons


def test_no_mutation_of_input():
    node = _high_node()
    original_severity = node.severity
    original_reason = node.reason_code

    result = _result_with_nodes(node)
    evaluate_regression_policy(result)

    assert node.severity == original_severity
    assert node.reason_code == original_reason
    assert len(result.nodes) == 1


# ---------------------------------------------------------------------------
# 8. PolicyDecision validation
# ---------------------------------------------------------------------------

def test_policy_decision_valid_statuses():
    for status in (POLICY_STATUS_PASS, POLICY_STATUS_WARN, POLICY_STATUS_FAIL):
        d = PolicyDecision(status=status)
        assert d.status == status


def test_policy_decision_invalid_status_raises():
    with pytest.raises(ValueError):
        PolicyDecision(status="INVALID")


def test_policy_decision_default_reasons_empty():
    d = PolicyDecision(status=POLICY_STATUS_PASS)
    assert d.reasons == []


def test_policy_decision_with_reasons():
    d = PolicyDecision(
        status=POLICY_STATUS_FAIL,
        reasons=["FAIL: 1 high severity regression(s) detected"],
    )
    assert len(d.reasons) == 1
