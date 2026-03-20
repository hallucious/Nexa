from dataclasses import dataclass
from typing import Dict, List

from src.engine.execution_regression_policy import PolicyDecision


@dataclass(frozen=True)
class ExplainabilityResult:
    status: str
    summary: str
    categories: Dict[str, List[str]]


def build_explainability(decision: PolicyDecision) -> ExplainabilityResult:
    structural: List[str] = []
    semantic: List[str] = []

    for reason in decision.reasons:
        if "signal" in reason:
            semantic.append(reason)
        else:
            structural.append(reason)

    if decision.status == "PASS":
        summary = "PASS: no issues"
    else:
        summary = f"{decision.status}: {len(structural)} structural issues, {len(semantic)} semantic issues"

    return ExplainabilityResult(
        status=decision.status,
        summary=summary,
        categories={
            "structural": structural,
            "semantic": semantic,
        },
    )
