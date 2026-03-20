from src.engine.alignment_engine import AlignmentResult, align_units
from src.engine.representation_model import ComparableUnit


def make_unit(
    unit_id: str,
    canonical_label: str | None,
    position: int,
    payload: str = "",
) -> ComparableUnit:
    return ComparableUnit(
        unit_id=unit_id,
        unit_kind="section",
        canonical_label=canonical_label,
        payload=payload,
        metadata={"position": position},
    )


def test_alignment_result_shape():
    result = AlignmentResult(matched_pairs=[], added_units=[], removed_units=[])
    assert result.matched_pairs == []
    assert result.added_units == []
    assert result.removed_units == []


def test_perfect_label_match():
    units_a = [
        make_unit("a1", "morning", 0),
        make_unit("a2", "lunch", 1),
    ]
    units_b = [
        make_unit("b1", "morning", 0),
        make_unit("b2", "lunch", 1),
    ]

    result = align_units(units_a, units_b)

    assert [(a.canonical_label, b.canonical_label) for a, b in result.matched_pairs] == [
        ("morning", "morning"),
        ("lunch", "lunch"),
    ]
    assert result.added_units == []
    assert result.removed_units == []


def test_partial_match_with_added_and_removed():
    units_a = [
        make_unit("a1", "morning", 0),
        make_unit("a2", "lunch", 1),
        make_unit("a3", "afternoon", 2),
    ]
    units_b = [
        make_unit("b1", "morning", 0),
        make_unit("b2", "afternoon", 1),
        make_unit("b3", "dinner", 2),
    ]

    result = align_units(units_a, units_b)

    assert [(a.canonical_label, b.canonical_label) for a, b in result.matched_pairs] == [
        ("morning", "morning"),
        ("afternoon", "afternoon"),
        ("lunch", "dinner"),
    ]
    assert result.added_units == []
    assert result.removed_units == []


def test_no_label_match_falls_back_to_position():
    units_a = [
        make_unit("a1", "alpha", 0),
        make_unit("a2", "beta", 1),
    ]
    units_b = [
        make_unit("b1", "gamma", 0),
        make_unit("b2", "delta", 1),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
        ("a2", "b2"),
    ]
    assert result.added_units == []
    assert result.removed_units == []


def test_different_lengths_creates_removed_units():
    units_a = [
        make_unit("a1", "morning", 0),
        make_unit("a2", "lunch", 1),
        make_unit("a3", "afternoon", 2),
    ]
    units_b = [
        make_unit("b1", "morning", 0),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
    ]
    assert [u.unit_id for u in result.removed_units] == ["a2", "a3"]
    assert result.added_units == []


def test_different_lengths_creates_added_units():
    units_a = [
        make_unit("a1", "morning", 0),
    ]
    units_b = [
        make_unit("b1", "morning", 0),
        make_unit("b2", "lunch", 1),
        make_unit("b3", "afternoon", 2),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
    ]
    assert result.removed_units == []
    assert [u.unit_id for u in result.added_units] == ["b2", "b3"]


def test_empty_input():
    result = align_units([], [])

    assert result.matched_pairs == []
    assert result.added_units == []
    assert result.removed_units == []


def test_duplicate_labels_match_in_order():
    units_a = [
        make_unit("a1", "section", 0, "A1"),
        make_unit("a2", "section", 1, "A2"),
    ]
    units_b = [
        make_unit("b1", "section", 0, "B1"),
        make_unit("b2", "section", 1, "B2"),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
        ("a2", "b2"),
    ]


def test_none_labels_use_positional_fallback():
    units_a = [
        make_unit("a1", None, 0),
        make_unit("a2", None, 1),
    ]
    units_b = [
        make_unit("b1", None, 0),
        make_unit("b2", None, 1),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
        ("a2", "b2"),
    ]
