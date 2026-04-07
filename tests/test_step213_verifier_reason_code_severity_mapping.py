from src.engine.execution_diff_model import CHANGE_TYPE_MODIFIED, RUN_DIFF_STATUS_CHANGED, NodeDiff, RunDiff
from src.engine.execution_regression_detector import REGRESSION_SEVERITY_HIGH, REGRESSION_SEVERITY_LOW, detect_regressions
from src.engine.execution_regression_policy import POLICY_STATUS_FAIL, POLICY_STATUS_PASS, evaluate_regression_policy


def test_minor_verifier_reason_code_downgrades_fail_transition_to_low_severity_pass():
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[
            NodeDiff(
                node_id="n1",
                change_type=CHANGE_TYPE_MODIFIED,
                left_status="success",
                right_status="success",
                left_verifier_status="pass",
                right_verifier_status="fail",
                left_verifier_reason_codes=[],
                right_verifier_reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"],
            )
        ],
    )

    result = detect_regressions(diff)

    assert len(result.verification) == 1
    assert result.verification[0].severity == REGRESSION_SEVERITY_LOW

    decision = evaluate_regression_policy(result)
    assert decision.status == POLICY_STATUS_PASS
    assert decision.reasons == ["PASS: no blocking regressions detected"]


def test_critical_verifier_reason_code_keeps_high_severity_fail():
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        node_diffs=[
            NodeDiff(
                node_id="n1",
                change_type=CHANGE_TYPE_MODIFIED,
                left_status="success",
                right_status="success",
                left_verifier_status="pass",
                right_verifier_status="warning",
                left_verifier_reason_codes=[],
                right_verifier_reason_codes=["STRUCTURE_REQUIRED_KEY_MISSING"],
            )
        ],
    )

    result = detect_regressions(diff)

    assert len(result.verification) == 1
    assert result.verification[0].severity == REGRESSION_SEVERITY_HIGH

    decision = evaluate_regression_policy(result)
    assert decision.status == POLICY_STATUS_FAIL
