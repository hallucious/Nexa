from src.engine.execution_diff_model import ArtifactDiff, CHANGE_TYPE_MODIFIED, RUN_DIFF_STATUS_CHANGED, RunDiff
from src.engine.execution_regression_detector import REGRESSION_SEVERITY_HIGH, REGRESSION_SEVERITY_LOW, detect_regressions
from src.engine.execution_regression_policy import POLICY_STATUS_FAIL, POLICY_STATUS_PASS, evaluate_regression_policy


def test_artifact_minor_validation_reason_code_downgrades_to_low_and_policy_pass():
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        artifact_diffs=[
            ArtifactDiff(
                artifact_id="artifact::report",
                change_type=CHANGE_TYPE_MODIFIED,
                left_validation_status="pass",
                right_validation_status="fail",
                left_validation_reason_codes=[],
                right_validation_reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"],
            )
        ],
    )

    result = detect_regressions(diff)

    assert len(result.verification) == 1
    assert result.verification[0].target_type == "artifact"
    assert result.verification[0].severity == REGRESSION_SEVERITY_LOW

    decision = evaluate_regression_policy(result)
    assert decision.status == POLICY_STATUS_PASS


def test_artifact_critical_validation_reason_code_keeps_high_and_policy_fail():
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        artifact_diffs=[
            ArtifactDiff(
                artifact_id="artifact::report",
                change_type=CHANGE_TYPE_MODIFIED,
                left_validation_status="pass",
                right_validation_status="warning",
                left_validation_reason_codes=[],
                right_validation_reason_codes=["STRUCTURE_REQUIRED_KEY_MISSING"],
            )
        ],
    )

    result = detect_regressions(diff)

    assert len(result.verification) == 1
    assert result.verification[0].severity == REGRESSION_SEVERITY_HIGH

    decision = evaluate_regression_policy(result)
    assert decision.status == POLICY_STATUS_FAIL
