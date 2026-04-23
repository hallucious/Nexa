from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .result import ValidationResult, Violation


def violations_as_dicts(violations: Iterable[Violation]) -> List[Dict[str, Any]]:
    return [
        {
            "rule_id": v.rule_id,
            "rule_name": v.rule_name,
            "severity": v.severity.value,
            "location_type": v.location_type,
            "location_id": v.location_id,
            "message": v.message,
        }
        for v in violations
    ]


def build_pre_validation_block(
    structural: ValidationResult,
    pre_determinism: Optional[ValidationResult],
) -> Dict[str, Any]:
    block: Dict[str, Any] = {
        "structural": {
            "performed": True,
            "success": structural.success,
            "violations": violations_as_dicts(structural.violations),
        },
    }

    if pre_determinism is not None:
        block["determinism"] = {
            "performed": True,
            "strict_mode": True,
            "success": pre_determinism.success,
            "violations": violations_as_dicts(pre_determinism.violations),
        }
    else:
        block["determinism"] = {"performed": False}

    return block


def build_post_validation_block(
    post_determinism: Optional[ValidationResult],
    *,
    strict_determinism: bool,
) -> Dict[str, Any]:
    if post_determinism is not None:
        return {
            "performed": True,
            "strict_mode": strict_determinism,
            "success": post_determinism.success,
            "violations": violations_as_dicts(post_determinism.violations),
        }
    return {"performed": False}


def build_decision_block(
    *,
    pre_value: str,
    pre_reason: str,
    post_value: str,
    post_reason: str,
) -> Dict[str, Any]:
    return {
        "pre": {"value": pre_value, "reason": pre_reason},
        "post": {"value": post_value, "reason": post_reason},
    }
