from src.engine.semantic_label_mapper import (
    LABEL_UNIT_ADDED,
    LABEL_UNIT_MODIFIED,
    LABEL_UNIT_REMOVED,
    LABEL_UNIT_REPLACED,
    map_to_semantic_labels,
)
from src.engine.change_signal_aggregator import AggregatedChangeSignal


def make(sig_type):
    return AggregatedChangeSignal(sig_type, "a", "b", ())


def test_replace_label():
    res = map_to_semantic_labels([make("REPLACE")])
    assert res[0].label == LABEL_UNIT_REPLACED


def test_add_label():
    res = map_to_semantic_labels([make("ADD")])
    assert res[0].label == LABEL_UNIT_ADDED


def test_remove_label():
    res = map_to_semantic_labels([make("REMOVE")])
    assert res[0].label == LABEL_UNIT_REMOVED


def test_mixed_label():
    res = map_to_semantic_labels([make("MIXED")])
    assert res[0].label == LABEL_UNIT_MODIFIED
