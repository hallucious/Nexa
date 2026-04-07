from src.contracts.verifier_reason_codes import (
    VERIFICATION_REGRESSION_CONTRACT_TABLE,
    VERIFICATION_TARGET_ARTIFACT,
    VERIFICATION_TARGET_NODE,
    get_verification_regression_fallback_severity,
    resolve_verification_regression_reason,
    resolve_verification_regression_severity,
)


def test_contract_table_contains_node_and_artifact_rows():
    targets = {row.target_type for row in VERIFICATION_REGRESSION_CONTRACT_TABLE}
    assert VERIFICATION_TARGET_NODE in targets
    assert VERIFICATION_TARGET_ARTIFACT in targets


def test_resolve_reason_uses_shared_contract_for_node_and_artifact():
    assert resolve_verification_regression_reason(VERIFICATION_TARGET_NODE, "pass", "fail") == "NODE_VERIFIER_PASS_TO_FAIL"
    assert resolve_verification_regression_reason(VERIFICATION_TARGET_ARTIFACT, "pass", "fail") == "ARTIFACT_VALIDATION_PASS_TO_FAIL"


def test_resolve_severity_prefers_detail_reason_codes_before_fallback():
    assert resolve_verification_regression_severity("NODE_VERIFIER_PASS_TO_WARNING", ["STRUCTURE_REQUIRED_KEY_MISSING"]) == "HIGH"
    assert get_verification_regression_fallback_severity("NODE_VERIFIER_PASS_TO_WARNING") == "MEDIUM"
