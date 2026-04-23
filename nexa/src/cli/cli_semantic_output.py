from src.engine.semantic_policy import SemanticPolicyDecision


def format_semantic_policy_output(decision: SemanticPolicyDecision) -> str:
    lines = []

    lines.append(f"Status: {decision.status}")
    lines.append(decision.summary)

    if decision.reasons:
        lines.append("Details:")
        for r in decision.reasons:
            lines.append(f"- {r}")

    return "\n".join(lines)
