from dataclasses import dataclass
from typing import List

from src.engine.semantic_label_mapper import SemanticLabel


POLICY_STATUS_PASS = "PASS"
POLICY_STATUS_WARN = "WARN"
POLICY_STATUS_FAIL = "FAIL"


@dataclass(frozen=True)
class SemanticPolicyDecision:
    status: str
    reasons: List[str]


def evaluate_semantic_policy(labels: List[SemanticLabel]) -> SemanticPolicyDecision:
    status = POLICY_STATUS_PASS
    reasons: List[str] = []

    for item in labels:
        label = item.label

        if label == "CONTENT_REMOVED":
            status = POLICY_STATUS_FAIL
            reasons.append("FAIL: critical content removed")

        elif label == "CONTENT_REPLACED":
            if status != POLICY_STATUS_FAIL:
                status = POLICY_STATUS_WARN
            reasons.append("WARN: content replaced")

        elif label == "CONTENT_ADDED":
            reasons.append("INFO: content added")

        elif label == "CONTENT_MODIFIED":
            if status == POLICY_STATUS_PASS:
                status = POLICY_STATUS_WARN
            reasons.append("WARN: content modified")

    return SemanticPolicyDecision(status=status, reasons=reasons)
