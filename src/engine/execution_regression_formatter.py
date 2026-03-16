"""
execution_regression_formatter.py

Formatters for RegressionResult from execution_regression_detector.

This module provides text and JSON formatters for regression detection results.

IMPORTANT: This is a pure formatter layer.
- No engine logic
- No detector logic
- No CLI imports
- Deterministic output
"""
from __future__ import annotations

from typing import Any, Dict

from src.engine.execution_regression_detector import RegressionResult


def format_regression_summary(result: RegressionResult) -> str:
    """Format a short summary of regression results.
    
    Returns a compact summary with status and counts.
    """
    lines = [
        "Execution Regression",
        f"status: {result.status}",
        f"nodes: {result.summary.node_regressions}",
        f"artifacts: {result.summary.artifact_regressions}",
        f"context: {result.summary.context_regressions}",
    ]
    return "\n".join(lines)


def format_regression(result: RegressionResult) -> str:
    """Format full regression result with details.
    
    Returns summary + detailed sections for each regression category.
    """
    lines = [format_regression_summary(result)]
    
    # Only add detail sections if regressions exist
    if not result.nodes and not result.artifacts and not result.context:
        return "\n".join(lines)
    
    # Node regressions section
    if result.nodes:
        lines.append("")
        lines.append("Node Regressions")
        lines.append("----------------")
        for node_reg in result.nodes:
            if node_reg.right_status is None:
                # Removed node
                lines.append(f"{node_reg.node_id}: removed (was {node_reg.left_status})")
            else:
                # Status change
                lines.append(f"{node_reg.node_id}: {node_reg.left_status} -> {node_reg.right_status}")
    
    # Artifact regressions section
    if result.artifacts:
        lines.append("")
        lines.append("Artifact Regressions")
        lines.append("--------------------")
        for art_reg in result.artifacts:
            lines.append(f"{art_reg.artifact_id}: {art_reg.reason}")
    
    # Context regressions section
    if result.context:
        lines.append("")
        lines.append("Context Regressions")
        lines.append("-------------------")
        for ctx_reg in result.context:
            lines.append(f"{ctx_reg.context_key}: {ctx_reg.reason}")
    
    return "\n".join(lines)


def format_regression_json(result: RegressionResult) -> Dict[str, Any]:
    """Format regression result as a JSON-serializable dict.
    
    Returns a dict suitable for json.dumps().
    Includes reason_code for stable programmatic access and reason for human readability.
    """
    return {
        "status": result.status,
        "summary": {
            "node_regressions": result.summary.node_regressions,
            "artifact_regressions": result.summary.artifact_regressions,
            "context_regressions": result.summary.context_regressions,
        },
        "nodes": [
            {
                "node_id": nr.node_id,
                "reason_code": nr.reason_code,
                "reason": nr.reason,
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
                "left_value": cr.left_value,
                "right_value": cr.right_value,
            }
            for cr in result.context
        ],
    }
