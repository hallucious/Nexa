from src.engine.cli_policy_integration import print_policy
from src.engine.semantic_policy import SemanticPolicyDecision


def make():
    return SemanticPolicyDecision(
        status="FAIL",
        reasons=["FAIL: critical content removed"],
        summary="FAIL: 1 semantic issues",
        categories={"semantic": ["FAIL: critical content removed"], "structural": []},
    )


def test_integration_output_contains_summary_and_status():
    out = print_policy(make())
    assert "FAIL" in out
    assert "semantic issues" in out
    assert "critical content removed" in out
