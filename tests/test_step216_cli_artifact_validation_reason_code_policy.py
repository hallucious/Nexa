from src.engine.cli_policy_integration import build_regression_result_from_summaries
from src.engine.execution_regression_policy import POLICY_STATUS_FAIL, POLICY_STATUS_PASS, evaluate_regression_policy


def test_cli_summary_artifact_minor_validation_reason_code_passes():
    baseline_payload = {
        "artifacts": {
            "artifact::report": {
                "validation_status": "pass",
                "validation_reason_codes": [],
            }
        }
    }
    current_payload = {
        "artifacts": {
            "artifact::report": {
                "validation_status": "fail",
                "validation_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
            }
        }
    }

    result = build_regression_result_from_summaries(baseline_payload, current_payload)
    decision = evaluate_regression_policy(result)

    assert len(result.verification) == 1
    assert result.verification[0].target_type == "artifact"
    assert result.verification[0].severity == "LOW"
    assert decision.status == POLICY_STATUS_PASS


def test_cli_summary_artifact_critical_validation_reason_code_fails():
    baseline_payload = {
        "artifacts": {
            "artifact::report": {
                "validation_status": "pass",
                "validation_reason_codes": [],
            }
        }
    }
    current_payload = {
        "artifacts": {
            "artifact::report": {
                "validation_status": "warning",
                "validation_reason_codes": ["STRUCTURE_REQUIRED_KEY_MISSING"],
            }
        }
    }

    result = build_regression_result_from_summaries(baseline_payload, current_payload)
    decision = evaluate_regression_policy(result)

    assert len(result.verification) == 1
    assert result.verification[0].severity == "HIGH"
    assert decision.status == POLICY_STATUS_FAIL
