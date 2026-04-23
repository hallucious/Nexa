"""
execution_regression_formatter.py

Formatters for RegressionResult from execution_regression_detector.
"""
from __future__ import annotations

from typing import Any, Dict

from src.contracts.verifier_reason_codes import explain_verification_regression_resolution
from src.engine.execution_regression_detector import RegressionResult


def format_regression_summary(result: RegressionResult) -> str:
    lines = [
        "Execution Regression",
        f"status: {result.status}",
        f"nodes: {result.summary.node_regressions}",
        f"artifacts: {result.summary.artifact_regressions}",
        f"context: {result.summary.context_regressions}",
        f"verification: {result.summary.verification_regressions}",
        f"severity: high={result.summary.high_regressions} medium={result.summary.medium_regressions} low={result.summary.low_regressions}",
    ]
    return "\n".join(lines)


def format_regression(result: RegressionResult) -> str:
    lines = [format_regression_summary(result)]
    if not result.nodes and not result.artifacts and not result.context and not result.verification:
        return "\n".join(lines)

    if result.nodes:
        lines.extend(["", "Node Regressions", "----------------"])
        for node_reg in result.nodes:
            if node_reg.right_status is None:
                lines.append(f"{node_reg.node_id}: removed (was {node_reg.left_status}) [{node_reg.severity}]")
            else:
                lines.append(f"{node_reg.node_id}: {node_reg.left_status} -> {node_reg.right_status} [{node_reg.severity}]")

    if result.artifacts:
        lines.extend(["", "Artifact Regressions", "--------------------"])
        for art_reg in result.artifacts:
            lines.append(f"{art_reg.artifact_id}: {art_reg.reason} [{art_reg.severity}]")

    if result.context:
        lines.extend(["", "Context Regressions", "-------------------"])
        for ctx_reg in result.context:
            lines.append(f"{ctx_reg.context_key}: {ctx_reg.reason} [{ctx_reg.severity}]")

    if result.verification:
        lines.extend(["", "Verification Regressions", "------------------------"])
        for ver_reg in result.verification:
            left = ver_reg.left_status if ver_reg.left_status is not None else "none"
            right = ver_reg.right_status if ver_reg.right_status is not None else "none"
            resolution = explain_verification_regression_resolution(
                ver_reg.target_type,
                ver_reg.left_status,
                ver_reg.right_status,
                ver_reg.right_reason_codes or ver_reg.left_reason_codes,
            )
            suffix = ""
            if resolution is not None:
                suffix = (
                    f" source={resolution.resolution_source}"
                    f" contract_reason={resolution.contract_reason_code}"
                    f" fallback={resolution.fallback_severity}"
                    f" detail={resolution.detail_severity or 'none'}"
                )
                if resolution.detail_reason_codes:
                    suffix += f" detail_codes={','.join(resolution.detail_reason_codes)}"
            lines.append(f"{ver_reg.target_type} {ver_reg.target_id}: {left} -> {right} ({ver_reg.reason}) [{ver_reg.severity}]{suffix}")

    return "\n".join(lines)


def format_regression_json(result: RegressionResult) -> Dict[str, Any]:
    return {
        "status": result.status,
        "summary": {
            "node_regressions": result.summary.node_regressions,
            "artifact_regressions": result.summary.artifact_regressions,
            "context_regressions": result.summary.context_regressions,
            "verification_regressions": result.summary.verification_regressions,
            "high_regressions": result.summary.high_regressions,
            "medium_regressions": result.summary.medium_regressions,
            "low_regressions": result.summary.low_regressions,
        },
        "nodes": [
            {
                "node_id": nr.node_id,
                "reason_code": nr.reason_code,
                "reason": nr.reason,
                "severity": nr.severity,
                "left_status": nr.left_status,
                "right_status": nr.right_status,
            }
            for nr in result.nodes
        ],
        "artifacts": [
            {
                "artifact_id": ar.artifact_id,
                "reason_code": ar.reason_code,
                "reason": ar.reason,
                "severity": ar.severity,
                "left_hash": ar.left_hash,
                "right_hash": ar.right_hash,
            }
            for ar in result.artifacts
        ],
        "context": [
            {
                "context_key": cr.context_key,
                "reason_code": cr.reason_code,
                "reason": cr.reason,
                "severity": cr.severity,
                "left_value": cr.left_value,
                "right_value": cr.right_value,
            }
            for cr in result.context
        ],
        "verification": [
            {
                "target_type": vr.target_type,
                "target_id": vr.target_id,
                "reason_code": vr.reason_code,
                "reason": vr.reason,
                "severity": vr.severity,
                "left_status": vr.left_status,
                "right_status": vr.right_status,
                "left_reason_codes": list(vr.left_reason_codes),
                "right_reason_codes": list(vr.right_reason_codes),
                "contract_resolution": (
                    lambda resolution: None if resolution is None else {
                        "resolution_source": resolution.resolution_source,
                        "contract_reason_code": resolution.contract_reason_code,
                        "fallback_severity": resolution.fallback_severity,
                        "detail_severity": resolution.detail_severity,
                        "detail_reason_codes": list(resolution.detail_reason_codes),
                        "resolved_severity": resolution.resolved_severity,
                    }
                )(
                    explain_verification_regression_resolution(
                        vr.target_type,
                        vr.left_status,
                        vr.right_status,
                        vr.right_reason_codes or vr.left_reason_codes,
                    )
                ),
            }
            for vr in result.verification
        ],
    }
