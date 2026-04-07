from src.engine.cli_policy_integration import build_regression_result_from_summaries
from src.engine.execution_regression_policy import POLICY_STATUS_PASS, evaluate_regression_policy


def test_cli_summary_minor_verifier_reason_code_passes_not_fails():
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
                "verifier_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
            }
        }
    }

    result = build_regression_result_from_summaries(baseline_payload, current_payload)
    decision = evaluate_regression_policy(result)

    assert len(result.verification) == 1
    assert result.verification[0].severity == "LOW"
    assert decision.status == POLICY_STATUS_PASS
