from src.engine.semantic_label_mapper import (
    LABEL_CONTENT_ADDED,
    LABEL_CONTENT_MODIFIED,
    LABEL_CONTENT_REMOVED,
    LABEL_CONTENT_REPLACED,
    map_to_semantic_labels,
)
from src.engine.change_signal_aggregator import AggregatedChangeSignal


def make(sig_type):
    return AggregatedChangeSignal(sig_type, "a", "b", ())


def test_replace_label():
    res = map_to_semantic_labels([make("REPLACE")])
    assert res[0].label == LABEL_CONTENT_REPLACED


def test_add_label():
    res = map_to_semantic_labels([make("ADD")])
    assert res[0].label == LABEL_CONTENT_ADDED


def test_remove_label():
    res = map_to_semantic_labels([make("REMOVE")])
    assert res[0].label == LABEL_CONTENT_REMOVED


def test_mixed_label():
    res = map_to_semantic_labels([make("MIXED")])
    assert res[0].label == LABEL_CONTENT_MODIFIED
