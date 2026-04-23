from src.cli.cli_policy_integration import print_policy
from src.engine.semantic_policy import SemanticPolicyDecision


def make():
    return SemanticPolicyDecision(
        status="FAIL",
        reasons=["FAIL: critical unit removed"],
        summary="FAIL: 1 semantic issues",
        categories={"semantic": ["FAIL: critical unit removed"], "structural": []},
    )


def test_integration_output_contains_summary_and_status():
    out = print_policy(make())
    assert "FAIL" in out
    assert "semantic issues" in out
    assert "critical unit removed" in out
