from src.cli.cli_policy_integration import build_regression_result_from_summaries
from src.engine.execution_regression_detector import detect_regressions
from src.engine.execution_diff_model import ArtifactDiff, NodeDiff, RunDiff


def test_cli_and_detector_share_node_and_artifact_verification_mapping():
    baseline = {
        "nodes": {"n1": {"verifier_status": "pass", "verifier_reason_codes": []}},
        "artifacts": {"a1": {"validation_status": "pass", "validation_reason_codes": []}},
    }
    current = {
        "nodes": {"n1": {"verifier_status": "warning", "verifier_reason_codes": ["STRUCTURE_REQUIRED_KEY_MISSING"]}},
        "artifacts": {"a1": {"validation_status": "warning", "validation_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"]}},
    }
    cli_result = build_regression_result_from_summaries(baseline, current)
    diff = RunDiff(
        left_run_id="left",
        right_run_id="right",
        status="changed",
        node_diffs=[NodeDiff(node_id="n1", change_type="modified", left_verifier_status="pass", right_verifier_status="warning", left_verifier_reason_codes=[], right_verifier_reason_codes=["STRUCTURE_REQUIRED_KEY_MISSING"])],
        artifact_diffs=[ArtifactDiff(artifact_id="a1", change_type="modified", left_validation_status="pass", right_validation_status="warning", left_validation_reason_codes=[], right_validation_reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"])],
    )
    detector_result = detect_regressions(diff)
    cli_codes = {(r.target_type, r.target_id, r.reason_code, r.severity) for r in cli_result.verification}
    det_codes = {(r.target_type, r.target_id, r.reason_code, r.severity) for r in detector_result.verification}
    assert ("node", "n1", "NODE_VERIFIER_PASS_TO_WARNING", "HIGH") in cli_codes
    assert ("artifact", "a1", "ARTIFACT_VALIDATION_PASS_TO_WARNING", "LOW") in cli_codes
    assert ("node", "n1", "NODE_VERIFIER_PASS_TO_WARNING", "HIGH") in det_codes
    assert ("artifact", "a1", "ARTIFACT_VALIDATION_PASS_TO_WARNING", "LOW") in det_codes
