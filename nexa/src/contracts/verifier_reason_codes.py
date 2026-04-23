from __future__ import annotations

STRUCTURE_OUTPUT_TYPE_MISMATCH = "STRUCTURE_OUTPUT_TYPE_MISMATCH"
STRUCTURE_REQUIRED_KEY_MISSING = "STRUCTURE_REQUIRED_KEY_MISSING"
REQUIREMENT_EMPTY_OUTPUT = "REQUIREMENT_EMPTY_OUTPUT"
REQUIREMENT_TEXT_TOO_SHORT = "REQUIREMENT_TEXT_TOO_SHORT"
REQUIREMENT_REQUIRED_TEXT_MISSING = "REQUIREMENT_REQUIRED_TEXT_MISSING"
LOGIC_FORBIDDEN_TEXT_PRESENT = "LOGIC_FORBIDDEN_TEXT_PRESENT"
LOGIC_FIELD_EQUALITY_VIOLATION = "LOGIC_FIELD_EQUALITY_VIOLATION"
UNKNOWN_VERIFIER_EXCEPTION = "UNKNOWN_VERIFIER_EXCEPTION"

VERIFIER_REASON_CODES = {
    STRUCTURE_OUTPUT_TYPE_MISMATCH,
    STRUCTURE_REQUIRED_KEY_MISSING,
    REQUIREMENT_EMPTY_OUTPUT,
    REQUIREMENT_TEXT_TOO_SHORT,
    REQUIREMENT_REQUIRED_TEXT_MISSING,
    LOGIC_FORBIDDEN_TEXT_PRESENT,
    LOGIC_FIELD_EQUALITY_VIOLATION,
    UNKNOWN_VERIFIER_EXCEPTION,
}

VERIFIER_REGRESSION_SEVERITY_HIGH = "HIGH"
VERIFIER_REGRESSION_SEVERITY_MEDIUM = "MEDIUM"
VERIFIER_REGRESSION_SEVERITY_LOW = "LOW"

VERIFIER_REASON_CODE_TO_REGRESSION_SEVERITY = {
    STRUCTURE_OUTPUT_TYPE_MISMATCH: VERIFIER_REGRESSION_SEVERITY_HIGH,
    STRUCTURE_REQUIRED_KEY_MISSING: VERIFIER_REGRESSION_SEVERITY_HIGH,
    REQUIREMENT_EMPTY_OUTPUT: VERIFIER_REGRESSION_SEVERITY_HIGH,
    REQUIREMENT_REQUIRED_TEXT_MISSING: VERIFIER_REGRESSION_SEVERITY_HIGH,
    LOGIC_FORBIDDEN_TEXT_PRESENT: VERIFIER_REGRESSION_SEVERITY_HIGH,
    UNKNOWN_VERIFIER_EXCEPTION: VERIFIER_REGRESSION_SEVERITY_HIGH,
    LOGIC_FIELD_EQUALITY_VIOLATION: VERIFIER_REGRESSION_SEVERITY_MEDIUM,
    REQUIREMENT_TEXT_TOO_SHORT: VERIFIER_REGRESSION_SEVERITY_LOW,
}

_VERIFIER_REGRESSION_SEVERITY_ORDER = {
    VERIFIER_REGRESSION_SEVERITY_LOW: 0,
    VERIFIER_REGRESSION_SEVERITY_MEDIUM: 1,
    VERIFIER_REGRESSION_SEVERITY_HIGH: 2,
}


def get_verifier_regression_severity(reason_codes: list[str] | tuple[str, ...] | set[str] | frozenset[str]) -> str | None:
    mapped = [
        VERIFIER_REASON_CODE_TO_REGRESSION_SEVERITY[code]
        for code in reason_codes
        if code in VERIFIER_REASON_CODE_TO_REGRESSION_SEVERITY
    ]
    if not mapped:
        return None
    return max(mapped, key=_VERIFIER_REGRESSION_SEVERITY_ORDER.__getitem__)


from dataclasses import dataclass
from typing import Iterable

VERIFICATION_TARGET_NODE = "node"
VERIFICATION_TARGET_ARTIFACT = "artifact"

@dataclass(frozen=True)
class VerificationRegressionContractRow:
    target_type: str
    left_status: str
    right_status: str
    regression_reason_code: str
    fallback_severity: str


@dataclass(frozen=True)
class VerificationRegressionResolution:
    target_type: str
    left_status: str | None
    right_status: str | None
    contract_reason_code: str
    fallback_severity: str
    detail_reason_codes: tuple[str, ...]
    detail_severity: str | None
    resolved_severity: str
    resolution_source: str


VERIFICATION_REGRESSION_CONTRACT_TABLE = (
    VerificationRegressionContractRow(VERIFICATION_TARGET_NODE, "pass", "fail", "NODE_VERIFIER_PASS_TO_FAIL", VERIFIER_REGRESSION_SEVERITY_HIGH),
    VerificationRegressionContractRow(VERIFICATION_TARGET_NODE, "pass", "warning", "NODE_VERIFIER_PASS_TO_WARNING", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_NODE, "pass", "inconclusive", "NODE_VERIFIER_PASS_TO_INCONCLUSIVE", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_NODE, "warning", "fail", "NODE_VERIFIER_WARNING_TO_FAIL", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_NODE, "inconclusive", "fail", "NODE_VERIFIER_INCONCLUSIVE_TO_FAIL", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_ARTIFACT, "pass", "fail", "ARTIFACT_VALIDATION_PASS_TO_FAIL", VERIFIER_REGRESSION_SEVERITY_HIGH),
    VerificationRegressionContractRow(VERIFICATION_TARGET_ARTIFACT, "pass", "warning", "ARTIFACT_VALIDATION_PASS_TO_WARNING", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_ARTIFACT, "pass", "inconclusive", "ARTIFACT_VALIDATION_PASS_TO_INCONCLUSIVE", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_ARTIFACT, "warning", "fail", "ARTIFACT_VALIDATION_WARNING_TO_FAIL", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
    VerificationRegressionContractRow(VERIFICATION_TARGET_ARTIFACT, "inconclusive", "fail", "ARTIFACT_VALIDATION_INCONCLUSIVE_TO_FAIL", VERIFIER_REGRESSION_SEVERITY_MEDIUM),
)


def get_verification_regression_contract_rows() -> tuple[VerificationRegressionContractRow, ...]:
    return VERIFICATION_REGRESSION_CONTRACT_TABLE


def find_verification_regression_contract_row(target_type: str, left_status: str | None, right_status: str | None) -> VerificationRegressionContractRow | None:
    for row in VERIFICATION_REGRESSION_CONTRACT_TABLE:
        if row.target_type == target_type and row.left_status == left_status and row.right_status == right_status:
            return row
    return None


def explain_verification_regression_resolution(
    target_type: str,
    left_status: str | None,
    right_status: str | None,
    detail_reason_codes: Iterable[str] | None = None,
) -> VerificationRegressionResolution | None:
    row = find_verification_regression_contract_row(target_type, left_status, right_status)
    if row is None:
        return None
    detail_codes = tuple(detail_reason_codes or ())
    detail_severity = get_verifier_regression_severity(detail_codes) if detail_codes else None
    if detail_severity is not None:
        resolved_severity = detail_severity
        resolution_source = "detail_reason_codes"
    else:
        resolved_severity = row.fallback_severity
        resolution_source = "contract_fallback"
    return VerificationRegressionResolution(
        target_type=target_type,
        left_status=left_status,
        right_status=right_status,
        contract_reason_code=row.regression_reason_code,
        fallback_severity=row.fallback_severity,
        detail_reason_codes=detail_codes,
        detail_severity=detail_severity,
        resolved_severity=resolved_severity,
        resolution_source=resolution_source,
    )


def resolve_verification_regression_reason(target_type: str, left_status: str | None, right_status: str | None) -> str | None:
    row = find_verification_regression_contract_row(target_type, left_status, right_status)
    return row.regression_reason_code if row is not None else None


def get_verification_regression_fallback_severity(reason_code: str) -> str | None:
    for row in VERIFICATION_REGRESSION_CONTRACT_TABLE:
        if row.regression_reason_code == reason_code:
            return row.fallback_severity
    return None


def resolve_verification_regression_severity(reason_code: str, detail_reason_codes: Iterable[str] | None) -> str | None:
    detail_codes = tuple(detail_reason_codes or ())
    detailed = get_verifier_regression_severity(detail_codes) if detail_codes else None
    if detailed is not None:
        return detailed
    return get_verification_regression_fallback_severity(reason_code)
