from __future__ import annotations

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



def test_alignment_result_defaults_are_empty():
    result = AlignmentResult()

    assert result.matched_pairs == []
    assert result.added_units == []
    assert result.removed_units == []



def test_align_units_matches_exact_labels_in_order():
    units_a = [
        make_unit("a1", "morning", 0),
        make_unit("a2", "lunch", 1),
    ]
    units_b = [
        make_unit("b1", "morning", 0),
        make_unit("b2", "lunch", 1),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
        ("a2", "b2"),
    ]
    assert result.added_units == []
    assert result.removed_units == []



def test_align_units_uses_positional_fallback_for_unmatched_units():
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

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [
        ("a1", "b1"),
        ("a3", "b2"),
        ("a2", "b3"),
    ]
    assert result.added_units == []
    assert result.removed_units == []



def test_align_units_handles_no_label_match_by_position():
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



def test_align_units_marks_leftover_a_units_as_removed():
    units_a = [
        make_unit("a1", "morning", 0),
        make_unit("a2", "lunch", 1),
        make_unit("a3", "afternoon", 2),
    ]
    units_b = [
        make_unit("b1", "morning", 0),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [("a1", "b1")]
    assert [unit.unit_id for unit in result.removed_units] == ["a2", "a3"]
    assert result.added_units == []



def test_align_units_marks_leftover_b_units_as_added():
    units_a = [make_unit("a1", "morning", 0)]
    units_b = [
        make_unit("b1", "morning", 0),
        make_unit("b2", "lunch", 1),
        make_unit("b3", "afternoon", 2),
    ]

    result = align_units(units_a, units_b)

    assert [(a.unit_id, b.unit_id) for a, b in result.matched_pairs] == [("a1", "b1")]
    assert result.removed_units == []
    assert [unit.unit_id for unit in result.added_units] == ["b2", "b3"]



def test_align_units_handles_empty_inputs():
    result = align_units([], [])

    assert result.matched_pairs == []
    assert result.added_units == []
    assert result.removed_units == []



def test_align_units_matches_duplicate_labels_in_order_of_appearance():
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



def test_align_units_uses_positional_fallback_for_none_labels():
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
