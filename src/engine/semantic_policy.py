from dataclasses import dataclass
from typing import Dict, List

from src.engine.semantic_label_mapper import SemanticLabel

POLICY_STATUS_PASS = "PASS"
POLICY_STATUS_WARN = "WARN"
POLICY_STATUS_FAIL = "FAIL"


@dataclass(frozen=True)
class SemanticPolicyDecision:
    status: str
    reasons: List[str]
    summary: str
    categories: Dict[str, List[str]]


def _init_categories() -> Dict[str, List[str]]:
    return {"semantic": [], "structural": []}


def _classify(label: str) -> str:
    # v1: all current labels are semantic
    return "semantic"


def _build_summary(status: str, categories: Dict[str, List[str]]) -> str:
    total_sem = len(categories.get("semantic", []))
    total_str = len(categories.get("structural", []))
    if status == POLICY_STATUS_PASS:
        return "PASS: no issues"
    parts = []
    if total_str:
        parts.append(f"{total_str} structural issues")
    if total_sem:
        parts.append(f"{total_sem} semantic issues")
    joined = ", ".join(parts) if parts else "no issues"
    return f"{status}: {joined}"


def evaluate_semantic_policy(labels: List[SemanticLabel]) -> SemanticPolicyDecision:
    status = POLICY_STATUS_PASS
    reasons: List[str] = []
    categories = _init_categories()

    for item in labels:
        label = item.label
        cat = _classify(label)

        if label == "CONTENT_REMOVED":
            status = POLICY_STATUS_FAIL
            msg = "FAIL: critical content removed"
            reasons.append(msg)
            categories[cat].append(msg)

        elif label == "CONTENT_REPLACED":
            if status != POLICY_STATUS_FAIL:
                status = POLICY_STATUS_WARN
            msg = "WARN: content replaced"
            reasons.append(msg)
            categories[cat].append(msg)

        elif label == "CONTENT_MODIFIED":
            if status == POLICY_STATUS_PASS:
                status = POLICY_STATUS_WARN
            msg = "WARN: content modified"
            reasons.append(msg)
            categories[cat].append(msg)

        elif label == "CONTENT_ADDED":
            msg = "INFO: content added"
            reasons.append(msg)
            categories[cat].append(msg)

    summary = _build_summary(status, categories)

    return SemanticPolicyDecision(
        status=status,
        reasons=reasons,
        summary=summary,
        categories=categories,
    )
