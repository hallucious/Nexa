from src.engine.semantic_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_PASS,
    POLICY_STATUS_WARN,
    evaluate_semantic_policy,
)
from src.engine.semantic_label_mapper import SemanticLabel
from src.engine.change_signal_aggregator import AggregatedChangeSignal


def make(label):
    return SemanticLabel(label, AggregatedChangeSignal("X", "a", "b", ()))


def test_pass_summary_and_categories_when_only_added():
    res = evaluate_semantic_policy([make("UNIT_ADDED")])
    assert res.status == POLICY_STATUS_PASS
    assert res.summary == "PASS: no issues"
    assert len(res.categories["semantic"]) == 1
    assert "INFO: unit added" in res.categories["semantic"]


def test_warn_with_replaced_has_semantic_category_and_summary():
    res = evaluate_semantic_policy([make("UNIT_REPLACED")])
    assert res.status == POLICY_STATUS_WARN
    assert "WARN" in res.summary
    assert "semantic issues" in res.summary
    assert len(res.categories["semantic"]) == 1


def test_fail_with_removed_overrides_and_summary():
    res = evaluate_semantic_policy([make("UNIT_REMOVED")])
    assert res.status == POLICY_STATUS_FAIL
    assert res.summary.startswith("FAIL:")
    assert len(res.categories["semantic"]) == 1


def test_mixed_labels_fail_overrides_warn():
    res = evaluate_semantic_policy([
        make("UNIT_REPLACED"),
        make("UNIT_REMOVED"),
    ])
    assert res.status == POLICY_STATUS_FAIL
    assert "semantic issues" in res.summary


def test_empty_input_pass():
    res = evaluate_semantic_policy([])
    assert res.status == POLICY_STATUS_PASS
    assert res.summary == "PASS: no issues"
    assert res.categories["semantic"] == []
    assert res.categories["structural"] == []
