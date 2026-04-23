from src.cli.cli_policy_integration import build_regression_result_from_summaries
from src.engine.execution_regression_policy import POLICY_STATUS_FAIL, evaluate_regression_policy


def test_cli_policy_regression_builder_detects_verifier_status_degradation():
    baseline_payload = {
        "nodes": {
            "n1": {
                "status": "SUCCESS",
                "verifier_status": "pass",
                "verifier_reason_codes": [],
            }
        }
    }
    current_payload = {
        "nodes": {
            "n1": {
                "status": "SUCCESS",
                "verifier_status": "fail",
                "verifier_reason_codes": ["STRUCTURE_REQUIRED_KEY_MISSING"],
            }
        }
    }

    result = build_regression_result_from_summaries(baseline_payload, current_payload)

    assert result.status == "regression"
    assert len(result.verification) == 1
    assert result.verification[0].target_type == "node"
    assert result.verification[0].target_id == "n1"

    decision = evaluate_regression_policy(result)
    assert decision.status == POLICY_STATUS_FAIL
    assert any("n1" in reason for reason in decision.reasons)
