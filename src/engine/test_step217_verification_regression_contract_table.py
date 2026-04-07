from src.contracts.regression_reason_codes import (
    ARTIFACT_VALIDATION_PASS_TO_FAIL,
    ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE,
    ARTIFACT_VALIDATION_PASS_TO_WARNING,
    ARTIFACT_VALIDATION_WARNING_TO_FAIL,
    NODE_VERIFIER_INCONCLUSIVE_TO_FAIL,
    NODE_VERIFIER_PASS_TO_FAIL,
    NODE_VERIFIER_PASS_TO_INCONCLUSIVE,
    NODE_VERIFIER_PASS_TO_WARNING,
    NODE_VERIFIER_WARNING_TO_FAIL,
)
from src.contracts.verifier_reason_codes import (
    REQUIREMENT_TEXT_TOO_SHORT,
    STRUCTURE_REQUIRED_KEY_MISSING,
    VERIFIER_REGRESSION_SEVERITY_HIGH,
    VERIFIER_REGRESSION_SEVERITY_LOW,
    get_verifier_regression_severity,
)


def test_contract_table_node_and_artifact_reason_codes_are_declared():
    expected = {
        NODE_VERIFIER_PASS_TO_FAIL,
        NODE_VERIFIER_PASS_TO_WARNING,
        NODE_VERIFIER_PASS_TO_INCONCLUSIVE,
        NODE_VERIFIER_WARNING_TO_FAIL,
        NODE_VERIFIER_INCONCLUSIVE_TO_FAIL,
        ARTIFACT_VALIDATION_PASS_TO_FAIL,
        ARTIFACT_VALIDATION_PASS_TO_WARNING,
        ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE,
        ARTIFACT_VALIDATION_WARNING_TO_FAIL,
    }
    assert len(expected) == 9


def test_shared_reason_code_severity_helper_prefers_highest_known_reason():
    assert get_verifier_regression_severity([
        REQUIREMENT_TEXT_TOO_SHORT,
        STRUCTURE_REQUIRED_KEY_MISSING,
    ]) == VERIFIER_REGRESSION_SEVERITY_HIGH


def test_shared_reason_code_severity_helper_can_return_low():
    assert get_verifier_regression_severity([
        REQUIREMENT_TEXT_TOO_SHORT,
    ]) == VERIFIER_REGRESSION_SEVERITY_LOW
