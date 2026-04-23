from src.engine.change_signal_aggregator import (
    AGGREGATED_SIGNAL_ADD,
    AGGREGATED_SIGNAL_MIXED,
    AGGREGATED_SIGNAL_REMOVE,
    AGGREGATED_SIGNAL_REPLACE,
    AggregatedChangeSignal,
    aggregate_change_signals,
)
from src.engine.change_signal_extractor import ChangeSignal


def test_empty_input_returns_empty_list():
    assert aggregate_change_signals([]) == []


def test_adjacent_replace_signals_are_merged():
    signals = [
        ChangeSignal("REPLACE", "ramen", "sushi"),
        ChangeSignal("REPLACE", "cola", "tea"),
    ]

    result = aggregate_change_signals(signals)

    assert result == [
        AggregatedChangeSignal(
            signal_type=AGGREGATED_SIGNAL_REPLACE,
            before="ramen cola",
            after="sushi tea",
            source_signals=tuple(signals),
        )
    ]


def test_adjacent_add_signals_are_merged():
    signals = [
        ChangeSignal("ADD", None, "extra"),
        ChangeSignal("ADD", None, "detail"),
    ]

    result = aggregate_change_signals(signals)

    assert result == [
        AggregatedChangeSignal(
            signal_type=AGGREGATED_SIGNAL_ADD,
            before=None,
            after="extra detail",
            source_signals=tuple(signals),
        )
    ]


def test_adjacent_remove_signals_are_merged():
    signals = [
        ChangeSignal("REMOVE", "constraint", None),
        ChangeSignal("REMOVE", "format", None),
    ]

    result = aggregate_change_signals(signals)

    assert result == [
        AggregatedChangeSignal(
            signal_type=AGGREGATED_SIGNAL_REMOVE,
            before="constraint format",
            after=None,
            source_signals=tuple(signals),
        )
    ]


def test_replace_followed_by_add_becomes_mixed_bundle():
    signals = [
        ChangeSignal("REPLACE", "ramen", "sushi"),
        ChangeSignal("ADD", None, "with tea"),
    ]

    result = aggregate_change_signals(signals)

    assert result == [
        AggregatedChangeSignal(
            signal_type=AGGREGATED_SIGNAL_MIXED,
            before="ramen",
            after="sushi with tea",
            source_signals=tuple(signals),
        )
    ]


def test_non_mergeable_sequence_starts_new_bundle():
    signals = [
        ChangeSignal("ADD", None, "new detail"),
        ChangeSignal("REMOVE", "old detail", None),
    ]

    result = aggregate_change_signals(signals)

    assert result == [
        AggregatedChangeSignal(
            signal_type=AGGREGATED_SIGNAL_ADD,
            before=None,
            after="new detail",
            source_signals=(signals[0],),
        ),
        AggregatedChangeSignal(
            signal_type=AGGREGATED_SIGNAL_REMOVE,
            before="old detail",
            after=None,
            source_signals=(signals[1],),
        ),
    ]


def test_order_is_preserved_across_multiple_bundles():
    signals = [
        ChangeSignal("REPLACE", "a", "b"),
        ChangeSignal("REPLACE", "c", "d"),
        ChangeSignal("ADD", None, "tail"),
        ChangeSignal("REMOVE", "footer", None),
    ]

    result = aggregate_change_signals(signals)

    assert [item.signal_type for item in result] == [
        AGGREGATED_SIGNAL_MIXED,
        AGGREGATED_SIGNAL_REMOVE,
    ]
    assert result[0].before == "a c"
    assert result[0].after == "b d tail"
    assert result[1].before == "footer"
