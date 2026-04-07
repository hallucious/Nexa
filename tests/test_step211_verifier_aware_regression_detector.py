from src.contracts.regression_reason_codes import (
    ARTIFACT_VALIDATION_PASS_TO_WARNING,
    NODE_VERIFIER_PASS_TO_FAIL,
)
from src.engine.execution_diff_model import (
    CHANGE_TYPE_MODIFIED,
    RUN_DIFF_STATUS_CHANGED,
    ArtifactDiff,
    DiffSummary,
    NodeDiff,
    RunDiff,
)
from src.engine.execution_regression_detector import REGRESSION_STATUS_REGRESSION, detect_regressions
from src.engine.execution_regression_formatter import format_regression, format_regression_json
from src.engine.execution_regression_policy import POLICY_STATUS_FAIL, POLICY_STATUS_WARN, evaluate_regression_policy


def test_detect_regressions_projects_verifier_aware_regressions():
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
                right_verifier_reason_codes=["STRUCTURE_REQUIRED_KEY_MISSING"],
            )
        ],
        artifact_diffs=[
            ArtifactDiff(
                artifact_id="validation_report",
                change_type=CHANGE_TYPE_MODIFIED,
                left_validation_status="pass",
                right_validation_status="warning",
            )
        ],
        summary=DiffSummary(verification_changes=2),
    )

    result = detect_regressions(diff)

    assert result.status == REGRESSION_STATUS_REGRESSION
    assert result.summary.verification_regressions == 2
    assert [reg.reason_code for reg in result.verification] == [
        NODE_VERIFIER_PASS_TO_FAIL,
        ARTIFACT_VALIDATION_PASS_TO_WARNING,
    ]


def test_verifier_aware_policy_and_formatter_behave_consistently():
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
            )
        ],
    )

    result = detect_regressions(diff)
    decision = evaluate_regression_policy(result)
    text_output = format_regression(result)
    json_output = format_regression_json(result)

    assert decision.status == POLICY_STATUS_FAIL
    assert "Verification Regressions" in text_output
    assert "node n1: pass -> fail" in text_output
    assert json_output["summary"]["verification_regressions"] == 1
    assert json_output["verification"][0]["reason_code"] == NODE_VERIFIER_PASS_TO_FAIL


def test_warning_only_verifier_regression_warns():
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status=RUN_DIFF_STATUS_CHANGED,
        artifact_diffs=[
            ArtifactDiff(
                artifact_id="validation_report",
                change_type=CHANGE_TYPE_MODIFIED,
                left_validation_status="pass",
                right_validation_status="warning",
            )
        ],
    )

    result = detect_regressions(diff)
    decision = evaluate_regression_policy(result)

    assert result.summary.verification_regressions == 1
    assert decision.status == POLICY_STATUS_WARN
