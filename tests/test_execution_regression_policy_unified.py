from src.engine.change_signal_extractor import ChangeSignal
from src.engine.execution_regression_detector import (
    ContextRegression,
    NodeRegression,
    RegressionResult,
)
from src.contracts.regression_reason_codes import (
    CONTEXT_KEY_REMOVED,
    CONTEXT_VALUE_CHANGED,
    NODE_SUCCESS_TO_FAILURE,
)
from src.engine.execution_regression_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_PASS,
    POLICY_STATUS_WARN,
    evaluate_unified_policy,
)


def _clean_result() -> RegressionResult:
    return RegressionResult(status="clean")


def _warn_result() -> RegressionResult:
    return RegressionResult(
        status="regression",
        context=[ContextRegression(context_key="ctx.key", reason_code=CONTEXT_KEY_REMOVED)],
    )


def _pass_with_low_result() -> RegressionResult:
    return RegressionResult(
        status="regression",
        context=[ContextRegression(context_key="output.value", reason_code=CONTEXT_VALUE_CHANGED)],
    )


def _fail_result() -> RegressionResult:
    return RegressionResult(
        status="regression",
        nodes=[NodeRegression(node_id="n1", reason_code=NODE_SUCCESS_TO_FAILURE, left_status="success", right_status="failure")],
    )


def test_pass_and_pass_returns_pass():
    result = evaluate_unified_policy(_clean_result(), [])
    assert result.status == POLICY_STATUS_PASS
    assert result.reasons == [
        "PASS: no blocking regressions detected",
        "PASS: no change signals detected",
    ]


def test_regression_fail_and_signal_pass_returns_fail():
    result = evaluate_unified_policy(_fail_result(), [])
    assert result.status == POLICY_STATUS_FAIL
    assert result.reasons[0].startswith("FAIL:")


def test_regression_pass_and_signal_fail_returns_fail():
    result = evaluate_unified_policy(
        _pass_with_low_result(),
        [ChangeSignal("REMOVE", before="lost", after=None)],
    )
    assert result.status == POLICY_STATUS_FAIL
    assert result.reasons[0] == "PASS: no blocking regressions detected"
    assert result.reasons[1] == 'FAIL: signal REMOVE (before="lost")'


def test_regression_warn_and_signal_pass_returns_warn():
    result = evaluate_unified_policy(_warn_result(), [])
    assert result.status == POLICY_STATUS_WARN


def test_regression_pass_and_signal_warn_returns_warn():
    result = evaluate_unified_policy(
        _pass_with_low_result(),
        [ChangeSignal("ADD", before=None, after="extra")],
    )
    assert result.status == POLICY_STATUS_WARN
    assert result.reasons == [
        "PASS: no blocking regressions detected",
        'WARN: signal ADD (after="extra")',
    ]


def test_fail_dominates_warn():
    result = evaluate_unified_policy(
        _fail_result(),
        [ChangeSignal("ADD", before=None, after="extra")],
    )
    assert result.status == POLICY_STATUS_FAIL


def test_reason_order_is_regression_then_signal():
    result = evaluate_unified_policy(
        _warn_result(),
        [ChangeSignal("ADD", before=None, after="B")],
    )
    assert result.reasons[0].startswith("WARN: 1 medium severity regression")
    assert result.reasons[1].startswith("Trigger:")
    assert result.reasons[2] == 'WARN: signal ADD (after="B")'
