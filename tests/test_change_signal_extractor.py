from src.engine.change_signal_extractor import ChangeSignal, extract_change_signals
from src.engine.diff_types import DiffOp


def test_extract_change_signals_replace_from_adjacent_delete_insert():
    diff_ops = [
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]

    assert extract_change_signals(diff_ops) == [
        ChangeSignal("REPLACE", before="ramen", after="sushi"),
    ]


def test_extract_change_signals_add_from_insert_only():
    diff_ops = [DiffOp("insert", "dessert")]

    assert extract_change_signals(diff_ops) == [
        ChangeSignal("ADD", before=None, after="dessert"),
    ]


def test_extract_change_signals_remove_from_delete_only():
    diff_ops = [DiffOp("delete", "spicy")]

    assert extract_change_signals(diff_ops) == [
        ChangeSignal("REMOVE", before="spicy", after=None),
    ]


def test_extract_change_signals_ignores_equal_ops():
    diff_ops = [
        DiffOp("equal", "I eat"),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
        DiffOp("equal", "today"),
    ]

    assert extract_change_signals(diff_ops) == [
        ChangeSignal("REPLACE", before="ramen", after="sushi"),
    ]


def test_extract_change_signals_mixed_sequence_preserves_order():
    diff_ops = [
        DiffOp("equal", "I"),
        DiffOp("delete", "eat"),
        DiffOp("insert", "ate"),
        DiffOp("equal", "ramen"),
        DiffOp("insert", "today"),
        DiffOp("delete", "dessert"),
    ]

    assert extract_change_signals(diff_ops) == [
        ChangeSignal("REPLACE", before="eat", after="ate"),
        ChangeSignal("ADD", before=None, after="today"),
        ChangeSignal("REMOVE", before="dessert", after=None),
    ]


def test_extract_change_signals_empty_input_returns_empty_list():
    assert extract_change_signals([]) == []


def test_extract_change_signals_non_adjacent_delete_insert_are_not_grouped():
    diff_ops = [
        DiffOp("delete", "ramen"),
        DiffOp("equal", "and"),
        DiffOp("insert", "sushi"),
    ]

    assert extract_change_signals(diff_ops) == [
        ChangeSignal("REMOVE", before="ramen", after=None),
        ChangeSignal("ADD", before=None, after="sushi"),
    ]
