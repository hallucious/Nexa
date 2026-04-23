from src.engine.execution_regression_detector import RegressionResult, RegressionSummary, VerificationRegression
from src.engine.execution_regression_policy import evaluate_regression_policy


def test_policy_decision_details_preserve_verification_contract_resolution():
    verification = VerificationRegression(
        target_type="artifact",
        target_id="art_1",
        reason_code="ARTIFACT_VALIDATION_PASS_TO_WARNING",
        left_status="pass",
        right_status="warning",
        right_reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"],
    )
    result = RegressionResult(
        status="regression",
        summary=RegressionSummary(verification_regressions=1, low_regressions=1),
        verification=[verification],
    )
    decision = evaluate_regression_policy(result)
    assert decision.status == "PASS"
    details = decision.details["verification_contracts"][0]
    assert details["target_type"] == "artifact"
    assert details["contract_resolution"]["contract_reason_code"] == "ARTIFACT_VALIDATION_PASS_TO_WARNING"
    assert details["contract_resolution"]["fallback_severity"] == "MEDIUM"
    assert details["contract_resolution"]["detail_severity"] == "LOW"
    assert details["contract_resolution"]["resolved_severity"] == "LOW"
