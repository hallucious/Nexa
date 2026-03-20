from src.engine.change_signal_extractor import ChangeSignal
from src.engine.execution_regression_policy import (
    POLICY_STATUS_FAIL,
    POLICY_STATUS_PASS,
    POLICY_STATUS_WARN,
    evaluate_change_signals,
)


def test_replace_signal_causes_fail():
    signals = [ChangeSignal("REPLACE", before="ramen", after="sushi")]
    result = evaluate_change_signals(signals)
    assert result.status == POLICY_STATUS_FAIL
    assert result.reasons == [
        'FAIL: signal REPLACE (before="ramen", after="sushi")'
    ]


def test_remove_signal_causes_fail():
    signals = [ChangeSignal("REMOVE", before="error handling", after=None)]
    result = evaluate_change_signals(signals)
    assert result.status == POLICY_STATUS_FAIL
    assert result.reasons == [
        'FAIL: signal REMOVE (before="error handling")'
    ]


def test_add_only_causes_warn():
    signals = [ChangeSignal("ADD", before=None, after="extra explanation")]
    result = evaluate_change_signals(signals)
    assert result.status == POLICY_STATUS_WARN
    assert result.reasons == [
        'WARN: signal ADD (after="extra explanation")'
    ]


def test_mixed_replace_and_add_is_fail():
    signals = [
        ChangeSignal("ADD", before=None, after="extra"),
        ChangeSignal("REPLACE", before="a", after="b"),
    ]
    result = evaluate_change_signals(signals)
    assert result.status == POLICY_STATUS_FAIL
    assert result.reasons == [
        'WARN: signal ADD (after="extra")',
        'FAIL: signal REPLACE (before="a", after="b")',
    ]


def test_empty_signals_is_pass():
    result = evaluate_change_signals([])
    assert result.status == POLICY_STATUS_PASS
    assert result.reasons == ["PASS: no change signals detected"]


def test_order_is_preserved():
    signals = [
        ChangeSignal("REMOVE", before="A", after=None),
        ChangeSignal("ADD", before=None, after="B"),
        ChangeSignal("REPLACE", before="C", after="D"),
    ]
    result = evaluate_change_signals(signals)
    assert result.reasons == [
        'FAIL: signal REMOVE (before="A")',
        'WARN: signal ADD (after="B")',
        'FAIL: signal REPLACE (before="C", after="D")',
    ]
