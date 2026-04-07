from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.engine.semantic_policy import SemanticPolicyDecision
from src.engine.cli_semantic_output import format_semantic_policy_output
from src.contracts.regression_reason_codes import (
    NODE_REMOVED_SUCCESS,
    NODE_SUCCESS_TO_FAILURE,
    NODE_SUCCESS_TO_SKIPPED,
)
from src.contracts.verifier_reason_codes import (
    VERIFICATION_TARGET_ARTIFACT,
    VERIFICATION_TARGET_NODE,
    resolve_verification_regression_reason,
)
from src.engine.execution_regression_detector import NodeRegression, RegressionResult, VerificationRegression
from src.engine.execution_regression_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_WARN,
    evaluate_regression_policy,
)


def print_policy(decision: SemanticPolicyDecision) -> str:
    """Safe integration wrapper for CLI policy output.
    Returns formatted string instead of printing directly for testability.
    """
    return format_semantic_policy_output(decision)


def build_regression_result_from_summaries(
    baseline_payload: Dict[str, Any],
    current_payload: Dict[str, Any],
) -> RegressionResult:
    baseline_nodes = baseline_payload.get("nodes") or {}
    current_nodes = current_payload.get("nodes") or {}

    regressions: list[NodeRegression] = []
    verification_regressions: list[VerificationRegression] = []

    for node_id in sorted(set(baseline_nodes) | set(current_nodes)):
        left = baseline_nodes.get(node_id)
        right = current_nodes.get(node_id)

        left_status = (left or {}).get("status")
        right_status = (right or {}).get("status")

        if left_status == "SUCCESS" and right_status == "FAILURE":
            regressions.append(
                NodeRegression(
                    node_id=node_id,
                    reason_code=NODE_SUCCESS_TO_FAILURE,
                    left_status="success",
                    right_status="failure",
                )
            )
        elif left_status == "SUCCESS" and right_status == "SKIPPED":
            regressions.append(
                NodeRegression(
                    node_id=node_id,
                    reason_code=NODE_SUCCESS_TO_SKIPPED,
                    left_status="success",
                    right_status="skipped",
                )
            )
        elif left_status == "SUCCESS" and right is None:
            regressions.append(
                NodeRegression(
                    node_id=node_id,
                    reason_code=NODE_REMOVED_SUCCESS,
                    left_status="success",
                    right_status=None,
                )
            )

        left_verifier_status = (left or {}).get("verifier_status")
        right_verifier_status = (right or {}).get("verifier_status")
        verifier_reason = resolve_verification_regression_reason(VERIFICATION_TARGET_NODE, left_verifier_status, right_verifier_status)
        if verifier_reason is not None:
            verification_regressions.append(
                VerificationRegression(
                    target_type="node",
                    target_id=node_id,
                    reason_code=verifier_reason,
                    left_status=left_verifier_status,
                    right_status=right_verifier_status,
                    left_reason_codes=list((left or {}).get("verifier_reason_codes") or []),
                    right_reason_codes=list((right or {}).get("verifier_reason_codes") or []),
                )
            )

    baseline_artifacts = baseline_payload.get("artifacts") or {}
    current_artifacts = current_payload.get("artifacts") or {}
    for artifact_id in sorted(set(baseline_artifacts) | set(current_artifacts)):
        left = baseline_artifacts.get(artifact_id)
        right = current_artifacts.get(artifact_id)
        left_validation_status = (left or {}).get("validation_status")
        right_validation_status = (right or {}).get("validation_status")
        verifier_reason = resolve_verification_regression_reason(VERIFICATION_TARGET_ARTIFACT, left_validation_status, right_validation_status)
        if verifier_reason is not None:
            verification_regressions.append(
                VerificationRegression(
                    target_type="artifact",
                    target_id=artifact_id,
                    reason_code=verifier_reason,
                    left_status=left_validation_status,
                    right_status=right_validation_status,
                    left_reason_codes=list((left or {}).get("validation_reason_codes") or []),
                    right_reason_codes=list((right or {}).get("validation_reason_codes") or []),
                )
            )

    if regressions or verification_regressions:
        return RegressionResult(status="regression", nodes=regressions, verification=verification_regressions)
    return RegressionResult(status="clean")


def load_policy_overrides(policy_config_path: Optional[str]) -> Optional[Dict[str, str]]:
    if not policy_config_path:
        return None
    payload = json.loads(Path(policy_config_path).read_text(encoding="utf-8"))
    overrides = payload.get("overrides")
    if overrides is None:
        return None
    if not isinstance(overrides, dict):
        raise ValueError("policy config 'overrides' must be an object")

    normalized: Dict[str, str] = {}
    for reason_code, severity in overrides.items():
        if not isinstance(reason_code, str) or not isinstance(severity, str):
            raise ValueError("policy config overrides must map strings to strings")
        normalized[reason_code] = severity
    return normalized


def render_regression_policy_output(policy_result: Any) -> str:
    status = getattr(policy_result, "status", None)
    reasons = list(getattr(policy_result, "reasons", []) or [])

    lines: list[str] = []
    if status is not None:
        lines.append(f"Status: {status}")
    if reasons:
        lines.extend(reasons)
    return "\n".join(lines) if lines else str(policy_result)


def apply_baseline_policy(
    payload: Dict[str, Any],
    baseline_path: Optional[str],
    policy_config_path: Optional[str] = None,
) -> tuple[Dict[str, Any], int]:
    if not baseline_path:
        return payload, 0

    baseline_payload = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    regression_result = build_regression_result_from_summaries(baseline_payload, payload)
    overrides = load_policy_overrides(policy_config_path)
    decision = evaluate_regression_policy(regression_result, overrides)

    enriched = dict(payload)
    enriched["policy"] = {
        "status": decision.status,
        "reasons": list(decision.reasons),
        "display": render_regression_policy_output(decision),
    }

    if decision.status == POLICY_STATUS_FAIL:
        return enriched, 2
    if decision.status == POLICY_STATUS_WARN:
        return enriched, 1
    return enriched, 0
