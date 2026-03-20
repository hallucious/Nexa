from src.engine.cli_semantic_output import format_semantic_policy_output
from src.engine.semantic_policy import SemanticPolicyDecision


def make(status, summary, reasons):
    return SemanticPolicyDecision(
        status=status,
        reasons=reasons,
        summary=summary,
        categories={"semantic": reasons, "structural": []},
    )


def test_pass_output():
    d = make("PASS", "PASS: no issues", [])
    out = format_semantic_policy_output(d)
    assert "PASS" in out
    assert "no issues" in out


def test_warn_output():
    d = make("WARN", "WARN: 1 semantic issues", ["WARN: unit replaced"])
    out = format_semantic_policy_output(d)
    assert "WARN" in out
    assert "unit replaced" in out


def test_fail_output():
    d = make("FAIL", "FAIL: 1 semantic issues", ["FAIL: critical unit removed"])
    out = format_semantic_policy_output(d)
    assert "FAIL" in out
    assert "critical unit removed" in out
