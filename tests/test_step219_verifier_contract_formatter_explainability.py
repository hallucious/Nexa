from src.engine.execution_regression_detector import RegressionResult, RegressionSummary, VerificationRegression
from src.engine.execution_regression_formatter import format_regression, format_regression_json
from src.engine.execution_regression_policy import evaluate_regression_policy
from src.policy.policy_explainability import build_explainability


def _verification_result():
    verification = VerificationRegression(
        target_type="node",
        target_id="n1",
        reason_code="NODE_VERIFIER_PASS_TO_FAIL",
        left_status="pass",
        right_status="fail",
        right_reason_codes=["STRUCTURE_REQUIRED_KEY_MISSING"],
    )
    return RegressionResult(
        status="regression",
        summary=RegressionSummary(verification_regressions=1, high_regressions=1),
        verification=[verification],
    )


def test_formatter_text_includes_contract_resolution_details():
    output = format_regression(_verification_result())
    assert "source=detail_reason_codes" in output
    assert "contract_reason=NODE_VERIFIER_PASS_TO_FAIL" in output
    assert "fallback=HIGH" in output
    assert "detail=HIGH" in output
    assert "detail_codes=STRUCTURE_REQUIRED_KEY_MISSING" in output


def test_formatter_json_includes_contract_resolution():
    payload = format_regression_json(_verification_result())
    entry = payload["verification"][0]
    assert entry["contract_resolution"]["resolution_source"] == "detail_reason_codes"
    assert entry["contract_resolution"]["contract_reason_code"] == "NODE_VERIFIER_PASS_TO_FAIL"
    assert entry["contract_resolution"]["fallback_severity"] == "HIGH"
    assert entry["contract_resolution"]["detail_reason_codes"] == ["STRUCTURE_REQUIRED_KEY_MISSING"]


def test_policy_explainability_surfaces_verification_contract_details():
    decision = evaluate_regression_policy(_verification_result())
    explain = build_explainability(decision)
    assert explain.verification_contracts
    assert "node:n1" in explain.verification_contracts[0]
    assert "source=detail_reason_codes" in explain.verification_contracts[0]
