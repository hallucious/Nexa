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


def test_pass_when_only_added():
    res = evaluate_semantic_policy([make("UNIT_ADDED")])
    assert res.status == POLICY_STATUS_PASS


def test_warn_when_replaced():
    res = evaluate_semantic_policy([make("UNIT_REPLACED")])
    assert res.status == POLICY_STATUS_WARN


def test_fail_when_removed():
    res = evaluate_semantic_policy([make("UNIT_REMOVED")])
    assert res.status == POLICY_STATUS_FAIL


def test_warn_when_modified():
    res = evaluate_semantic_policy([make("UNIT_MODIFIED")])
    assert res.status == POLICY_STATUS_WARN


def test_fail_overrides_warn():
    res = evaluate_semantic_policy([
        make("UNIT_REPLACED"),
        make("UNIT_REMOVED"),
    ])
    assert res.status == POLICY_STATUS_FAIL
