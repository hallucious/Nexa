from src.engine.semantic_policy import SemanticPolicyDecision
from src.engine.cli_semantic_output import format_semantic_policy_output


def print_policy(decision: SemanticPolicyDecision) -> str:
    """Safe integration wrapper for CLI policy output.
    Returns formatted string instead of printing directly for testability.
    """
    return format_semantic_policy_output(decision)
