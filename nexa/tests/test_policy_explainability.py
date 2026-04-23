from src.contracts.policy_result_contract import PolicyDecision
from src.policy.policy_explainability import build_explainability


def test_structural_only():
    decision = PolicyDecision(
        status="FAIL",
        reasons=["FAIL: node n1 issue"]
    )

    result = build_explainability(decision)

    assert result.categories["structural"] == ["FAIL: node n1 issue"]
    assert result.categories["semantic"] == []
    assert result.summary == "FAIL: 1 structural issues, 0 semantic issues"


def test_semantic_only():
    decision = PolicyDecision(
        status="WARN",
        reasons=['WARN: signal ADD (after="x")']
    )

    result = build_explainability(decision)

    assert result.categories["structural"] == []
    assert result.categories["semantic"] == ['WARN: signal ADD (after="x")']
    assert result.summary == "WARN: 0 structural issues, 1 semantic issues"


def test_mixed():
    decision = PolicyDecision(
        status="FAIL",
        reasons=[
            "FAIL: node n1 issue",
            'FAIL: signal REPLACE (before="a", after="b")'
        ]
    )

    result = build_explainability(decision)

    assert result.categories["structural"] == ["FAIL: node n1 issue"]
    assert result.categories["semantic"] == ['FAIL: signal REPLACE (before="a", after="b")']
    assert result.summary == "FAIL: 1 structural issues, 1 semantic issues"


def test_empty_pass():
    decision = PolicyDecision(status="PASS", reasons=[])

    result = build_explainability(decision)

    assert result.summary == "PASS: no issues"
    assert result.categories["structural"] == []
    assert result.categories["semantic"] == []


def test_counts_accuracy():
    decision = PolicyDecision(
        status="WARN",
        reasons=[
            "WARN: node n1 issue",
            "WARN: node n2 issue",
            'WARN: signal ADD (after="x")'
        ]
    )

    result = build_explainability(decision)

    assert len(result.categories["structural"]) == 2
    assert len(result.categories["semantic"]) == 1
    assert result.summary == "WARN: 2 structural issues, 1 semantic issues"
