from src.engine.cli_policy_integration import build_regression_result_from_summaries


def test_cli_builds_node_verification_regression_from_shared_status_mapping():
    baseline = {
        "nodes": {
            "n1": {
                "verifier_status": "pass",
                "verifier_reason_codes": [],
            }
        }
    }
    current = {
        "nodes": {
            "n1": {
                "verifier_status": "fail",
                "verifier_reason_codes": ["STRUCTURE_REQUIRED_KEY_MISSING"],
            }
        }
    }
    result = build_regression_result_from_summaries(baseline, current)
    assert result.status == "regression"
    assert len(result.verification) == 1
    assert result.verification[0].target_type == "node"
    assert result.verification[0].target_id == "n1"


def test_cli_builds_artifact_verification_regression_from_shared_status_mapping():
    baseline = {
        "artifacts": {
            "a1": {
                "validation_status": "pass",
                "validation_reason_codes": [],
            }
        }
    }
    current = {
        "artifacts": {
            "a1": {
                "validation_status": "warning",
                "validation_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
            }
        }
    }
    result = build_regression_result_from_summaries(baseline, current)
    assert result.status == "regression"
    assert len(result.verification) == 1
    assert result.verification[0].target_type == "artifact"
    assert result.verification[0].target_id == "a1"
