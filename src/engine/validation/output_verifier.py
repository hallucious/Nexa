from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import json

from src.contracts.artifact_contract import infer_artifact_type
from src.contracts.verifier_reason_codes import (
    LOGIC_FIELD_EQUALITY_VIOLATION,
    LOGIC_FORBIDDEN_TEXT_PRESENT,
    REQUIREMENT_EMPTY_OUTPUT,
    REQUIREMENT_REQUIRED_TEXT_MISSING,
    REQUIREMENT_TEXT_TOO_SHORT,
    STRUCTURE_OUTPUT_TYPE_MISMATCH,
    STRUCTURE_REQUIRED_KEY_MISSING,
    UNKNOWN_VERIFIER_EXCEPTION,
)
from src.models.evaluation_models import (
    BranchAdvice,
    CompositeVerifierResult,
    EscalationAdvice,
    RetryAdvice,
    VerifierFinding,
    VerifierResult,
)


_STATUS_PRIORITY = {"pass": 0, "warning": 1, "inconclusive": 2, "fail": 3}


class OutputVerifierError(ValueError):
    """Raised when verifier configuration is malformed."""



def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)



def _status_from_findings(findings: list[VerifierFinding]) -> str:
    if any(f.severity in {"critical", "error"} for f in findings):
        return "fail"
    if any(f.severity == "warning" for f in findings):
        return "warning"
    return "pass"



def _score_from_findings(total_checks: int, findings: list[VerifierFinding]) -> float:
    if total_checks <= 0:
        return 1.0
    penalty = 0.0
    for finding in findings:
        if finding.severity == "critical":
            penalty += 1.0
        elif finding.severity == "error":
            penalty += 1.0
        elif finding.severity == "warning":
            penalty += 0.5
        else:
            penalty += 0.1
    score = max(0.0, 1.0 - (penalty / float(total_checks)))
    return round(score, 4)



def _advice_from_status(status: str) -> tuple[RetryAdvice, BranchAdvice, EscalationAdvice, str]:
    if status == "pass":
        return RetryAdvice(), BranchAdvice(), EscalationAdvice(), "continue"
    if status == "warning":
        return RetryAdvice(), BranchAdvice(), EscalationAdvice(), "continue_with_warnings"
    if status == "inconclusive":
        return (
            RetryAdvice(should_retry=True, strategy="verify_more", reason="verifier_inconclusive"),
            BranchAdvice(should_branch=False),
            EscalationAdvice(should_escalate=False),
            "verify_more",
        )
    return (
        RetryAdvice(should_retry=True, strategy="repair_output", reason="verification_failed"),
        BranchAdvice(should_branch=False),
        EscalationAdvice(should_escalate=False),
        "retry",
    )



def _build_result(
    *,
    verifier_id: str,
    verifier_type: str,
    target_ref: str,
    findings: list[VerifierFinding],
    total_checks: int,
    default_reason_code: str,
    explanation: str,
) -> VerifierResult:
    status = _status_from_findings(findings)
    retry_advice, branch_advice, escalation_advice, _ = _advice_from_status(status)
    reason_code = findings[0].reason_code if findings else default_reason_code
    return VerifierResult(
        verifier_id=verifier_id,
        verifier_type=verifier_type,
        target_ref=target_ref,
        status=status,
        score=_score_from_findings(total_checks, findings),
        confidence=1.0 if status == "pass" else 0.5,
        reason_code=reason_code,
        findings=findings,
        retry_advice=retry_advice,
        branch_advice=branch_advice,
        escalation_advice=escalation_advice,
        explanation=explanation,
    )



def _validate_mapping_output(output: Any) -> Dict[str, Any]:
    if not isinstance(output, dict):
        raise TypeError("output must be dict for mapping-based verification")
    return output



def run_structural_verifier(output: Any, spec: Dict[str, Any], *, target_ref: str) -> VerifierResult:
    verifier_id = str(spec.get("verifier_id") or "structural_verifier")
    expected_artifact_type = spec.get("expected_artifact_type")
    required_keys = spec.get("required_keys") or []
    if expected_artifact_type is not None and not isinstance(expected_artifact_type, str):
        raise OutputVerifierError("expected_artifact_type must be string")
    if not isinstance(required_keys, list) or not all(isinstance(x, str) and x for x in required_keys):
        raise OutputVerifierError("required_keys must be list[str]")

    findings: list[VerifierFinding] = []
    total_checks = 0

    if expected_artifact_type:
        total_checks += 1
        actual_type = infer_artifact_type(output)
        if actual_type != expected_artifact_type:
            findings.append(
                VerifierFinding(
                    finding_id=f"{verifier_id}::type",
                    severity="error",
                    category="structure",
                    reason_code=STRUCTURE_OUTPUT_TYPE_MISMATCH,
                    message=f"expected output type '{expected_artifact_type}', got '{actual_type}'",
                    suggested_action="align output type or insert explicit transform",
                )
            )

    if required_keys:
        total_checks += len(required_keys)
        try:
            mapping_output = _validate_mapping_output(output)
        except TypeError:
            for key in required_keys:
                findings.append(
                    VerifierFinding(
                        finding_id=f"{verifier_id}::missing::{key}",
                        severity="error",
                        category="structure",
                        reason_code=STRUCTURE_REQUIRED_KEY_MISSING,
                        message=f"required key '{key}' cannot be validated because output is not a mapping",
                        suggested_action="return a mapping output or relax required_keys",
                    )
                )
        else:
            for key in required_keys:
                if key not in mapping_output:
                    findings.append(
                        VerifierFinding(
                            finding_id=f"{verifier_id}::missing::{key}",
                            severity="error",
                            category="structure",
                            reason_code=STRUCTURE_REQUIRED_KEY_MISSING,
                            message=f"required key '{key}' is missing",
                            suggested_action="populate the missing field before downstream use",
                        )
                    )

    return _build_result(
        verifier_id=verifier_id,
        verifier_type="structural",
        target_ref=target_ref,
        findings=findings,
        total_checks=total_checks,
        default_reason_code="STRUCTURE_OK",
        explanation="structural verification completed",
    )



def run_requirement_verifier(output: Any, spec: Dict[str, Any], *, target_ref: str) -> VerifierResult:
    verifier_id = str(spec.get("verifier_id") or "requirement_verifier")
    allow_empty = bool(spec.get("allow_empty", True))
    min_text_length = spec.get("min_text_length")
    required_text_fragments = spec.get("required_text_fragments") or []
    if min_text_length is not None and (not isinstance(min_text_length, int) or min_text_length < 0):
        raise OutputVerifierError("min_text_length must be non-negative int when present")
    if not isinstance(required_text_fragments, list) or not all(isinstance(x, str) and x for x in required_text_fragments):
        raise OutputVerifierError("required_text_fragments must be list[str]")

    findings: list[VerifierFinding] = []
    total_checks = 1 + (1 if min_text_length is not None else 0) + len(required_text_fragments)

    output_text = _stringify(output)
    if not allow_empty:
        is_empty = output is None or output == "" or output == {} or output == []
        if is_empty:
            findings.append(
                VerifierFinding(
                    finding_id=f"{verifier_id}::empty",
                    severity="error",
                    category="requirement",
                    reason_code=REQUIREMENT_EMPTY_OUTPUT,
                    message="output is empty",
                    suggested_action="produce a non-empty output before continuing",
                )
            )

    if min_text_length is not None and len(output_text.strip()) < min_text_length:
        findings.append(
            VerifierFinding(
                finding_id=f"{verifier_id}::length",
                severity="warning",
                category="requirement",
                reason_code=REQUIREMENT_TEXT_TOO_SHORT,
                message=f"output text length is below minimum {min_text_length}",
                suggested_action="expand the response or lower min_text_length",
            )
        )

    lowered_text = output_text.lower()
    for fragment in required_text_fragments:
        if fragment.lower() not in lowered_text:
            findings.append(
                VerifierFinding(
                    finding_id=f"{verifier_id}::fragment::{fragment}",
                    severity="warning",
                    category="requirement",
                    reason_code=REQUIREMENT_REQUIRED_TEXT_MISSING,
                    message=f"required text fragment '{fragment}' is missing",
                    suggested_action="include the required fragment or revise requirement set",
                )
            )

    return _build_result(
        verifier_id=verifier_id,
        verifier_type="requirement",
        target_ref=target_ref,
        findings=findings,
        total_checks=total_checks,
        default_reason_code="REQUIREMENT_OK",
        explanation="requirement verification completed",
    )



def run_logical_verifier(output: Any, spec: Dict[str, Any], *, target_ref: str) -> VerifierResult:
    verifier_id = str(spec.get("verifier_id") or "logical_verifier")
    forbidden_substrings = spec.get("forbidden_substrings") or []
    disallow_equal_fields = spec.get("disallow_equal_fields") or []
    if not isinstance(forbidden_substrings, list) or not all(isinstance(x, str) and x for x in forbidden_substrings):
        raise OutputVerifierError("forbidden_substrings must be list[str]")
    if not isinstance(disallow_equal_fields, list):
        raise OutputVerifierError("disallow_equal_fields must be list")

    findings: list[VerifierFinding] = []
    total_checks = max(1, len(forbidden_substrings) + len(disallow_equal_fields))
    output_text = _stringify(output).lower()

    for fragment in forbidden_substrings:
        if fragment.lower() in output_text:
            findings.append(
                VerifierFinding(
                    finding_id=f"{verifier_id}::forbidden::{fragment}",
                    severity="warning",
                    category="logic",
                    reason_code=LOGIC_FORBIDDEN_TEXT_PRESENT,
                    message=f"forbidden logical marker '{fragment}' detected",
                    suggested_action="review the output for contradiction or unsupported conclusion",
                )
            )

    if isinstance(output, dict):
        for pair in disallow_equal_fields:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise OutputVerifierError("disallow_equal_fields entries must be [left, right]")
            left, right = pair
            if not isinstance(left, str) or not isinstance(right, str):
                raise OutputVerifierError("disallow_equal_fields entries must contain strings")
            if left in output and right in output and output.get(left) == output.get(right):
                findings.append(
                    VerifierFinding(
                        finding_id=f"{verifier_id}::fields::{left}::{right}",
                        severity="warning",
                        category="logic",
                        reason_code=LOGIC_FIELD_EQUALITY_VIOLATION,
                        message=f"fields '{left}' and '{right}' unexpectedly share the same value",
                        suggested_action="check whether both fields should really be identical",
                    )
                )

    return _build_result(
        verifier_id=verifier_id,
        verifier_type="logical",
        target_ref=target_ref,
        findings=findings,
        total_checks=total_checks,
        default_reason_code="LOGIC_OK",
        explanation="logical verification completed",
    )



def _normalize_verifier_specs(verifier_config: Dict[str, Any]) -> list[Dict[str, Any]]:
    if not isinstance(verifier_config, dict):
        raise OutputVerifierError("verifier config must be dict")
    modes = verifier_config.get("modes")
    if modes is None:
        return [dict(verifier_config)]
    if not isinstance(modes, list) or not all(isinstance(x, dict) for x in modes):
        raise OutputVerifierError("verifier.modes must be list[dict]")
    normalized: list[Dict[str, Any]] = []
    for index, item in enumerate(modes, start=1):
        merged = dict(verifier_config)
        merged.pop("modes", None)
        merged.update(item)
        merged.setdefault("verifier_id", f"{verifier_config.get('verifier_id', 'verifier')}::{index}")
        normalized.append(merged)
    return normalized



def aggregate_verifier_results(
    results: List[VerifierResult],
    *,
    target_ref: str,
) -> CompositeVerifierResult:
    if not results:
        return CompositeVerifierResult(
            target_ref=target_ref,
            constituent_results=[],
            aggregate_status="inconclusive",
            aggregate_score=None,
            aggregate_confidence=None,
            blocking_reason_codes=[],
            recommended_next_step="verify_more",
        )

    aggregate_status = max(results, key=lambda item: _STATUS_PRIORITY[item.status]).status
    scores = [item.score for item in results if item.score is not None]
    confidences = [item.confidence for item in results if item.confidence is not None]
    blocking_reason_codes = [item.reason_code for item in results if item.status == "fail"]
    _, _, _, default_next_step = _advice_from_status(aggregate_status)
    return CompositeVerifierResult(
        target_ref=target_ref,
        constituent_results=list(results),
        aggregate_status=aggregate_status,
        aggregate_score=round(sum(scores) / len(scores), 4) if scores else None,
        aggregate_confidence=round(sum(confidences) / len(confidences), 4) if confidences else None,
        blocking_reason_codes=blocking_reason_codes,
        recommended_next_step=default_next_step,
    )



def run_output_verifier(output: Any, verifier_config: Dict[str, Any], *, target_ref: str) -> CompositeVerifierResult:
    results: list[VerifierResult] = []
    for spec in _normalize_verifier_specs(verifier_config):
        verifier_type = str(spec.get("verifier_type") or "structural")
        try:
            if verifier_type == "structural":
                result = run_structural_verifier(output, spec, target_ref=target_ref)
            elif verifier_type == "requirement":
                result = run_requirement_verifier(output, spec, target_ref=target_ref)
            elif verifier_type == "logical":
                result = run_logical_verifier(output, spec, target_ref=target_ref)
            else:
                raise OutputVerifierError(f"unsupported verifier_type: {verifier_type}")
        except Exception as exc:
            if isinstance(exc, OutputVerifierError):
                raise
            result = VerifierResult(
                verifier_id=str(spec.get("verifier_id") or verifier_type),
                verifier_type=verifier_type if verifier_type in {"structural", "logical", "requirement", "policy", "evidence", "composite"} else "composite",
                target_ref=target_ref,
                status="inconclusive",
                score=0.0,
                confidence=0.0,
                reason_code=UNKNOWN_VERIFIER_EXCEPTION,
                findings=[
                    VerifierFinding(
                        finding_id=f"{spec.get('verifier_id', verifier_type)}::exception",
                        severity="warning",
                        category="unknown",
                        reason_code=UNKNOWN_VERIFIER_EXCEPTION,
                        message=f"verifier raised {type(exc).__name__}: {exc}",
                        suggested_action="inspect verifier configuration or verifier implementation",
                    )
                ],
                retry_advice=RetryAdvice(should_retry=True, strategy="verify_more", reason="verifier_exception"),
                branch_advice=BranchAdvice(),
                escalation_advice=EscalationAdvice(),
                explanation="verifier raised unexpected exception",
            )
        results.append(result)
    return aggregate_verifier_results(results, target_ref=target_ref)
