from src.engine.alignment_engine import AlignmentResult
from src.engine.representation_model import ComparableUnit
from src.engine.unit_diff_engine import UnitChange, UnitDiffResult, compare_aligned_units


def make_unit(
    unit_id: str,
    canonical_label: str | None,
    payload: str,
    position: int,
) -> ComparableUnit:
    return ComparableUnit(
        unit_id=unit_id,
        unit_kind="section",
        canonical_label=canonical_label,
        payload=payload,
        metadata={"position": position},
    )


def test_unit_change_shape():
    unit = make_unit("u1", "morning", "hello", 0)
    change = UnitChange(change_type="unchanged", unit_a=unit, unit_b=unit)

    assert change.change_type == "unchanged"
    assert change.unit_a == unit
    assert change.unit_b == unit


def test_unit_diff_result_shape():
    result = UnitDiffResult(changes=[], summary={"added": 0, "removed": 0, "modified": 0, "unchanged": 0})

    assert result.changes == []
    assert result.summary == {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "unchanged": 0,
    }


def test_unchanged_pair():
    unit_a = make_unit("a1", "morning", "same payload", 0)
    unit_b = make_unit("b1", "morning", "same payload", 0)
    alignment = AlignmentResult(matched_pairs=[(unit_a, unit_b)], added_units=[], removed_units=[])

    result = compare_aligned_units(alignment)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == "unchanged"
    assert result.summary == {"added": 0, "removed": 0, "modified": 0, "unchanged": 1}


def test_modified_pair():
    unit_a = make_unit("a1", "lunch", "eat ramen", 0)
    unit_b = make_unit("b1", "lunch", "eat sushi", 0)
    alignment = AlignmentResult(matched_pairs=[(unit_a, unit_b)], added_units=[], removed_units=[])

    result = compare_aligned_units(alignment)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == "modified"
    assert result.summary == {"added": 0, "removed": 0, "modified": 1, "unchanged": 0}


def test_removed_unit():
    unit_a = make_unit("a1", "dinner", "go to izakaya", 0)
    alignment = AlignmentResult(matched_pairs=[], added_units=[], removed_units=[unit_a])

    result = compare_aligned_units(alignment)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == "removed"
    assert result.changes[0].unit_a == unit_a
    assert result.changes[0].unit_b is None
    assert result.summary == {"added": 0, "removed": 1, "modified": 0, "unchanged": 0}


def test_added_unit():
    unit_b = make_unit("b1", "dinner", "go to bar", 0)
    alignment = AlignmentResult(matched_pairs=[], added_units=[unit_b], removed_units=[])

    result = compare_aligned_units(alignment)

    assert len(result.changes) == 1
    assert result.changes[0].change_type == "added"
    assert result.changes[0].unit_a is None
    assert result.changes[0].unit_b == unit_b
    assert result.summary == {"added": 1, "removed": 0, "modified": 0, "unchanged": 0}


def test_mixed_result():
    unchanged_a = make_unit("a1", "morning", "same", 0)
    unchanged_b = make_unit("b1", "morning", "same", 0)
    modified_a = make_unit("a2", "lunch", "ramen", 1)
    modified_b = make_unit("b2", "lunch", "sushi", 1)
    removed_a = make_unit("a3", "afternoon", "museum", 2)
    added_b = make_unit("b3", "dinner", "bar", 2)

    alignment = AlignmentResult(
        matched_pairs=[(unchanged_a, unchanged_b), (modified_a, modified_b)],
        added_units=[added_b],
        removed_units=[removed_a],
    )

    result = compare_aligned_units(alignment)

    assert [change.change_type for change in result.changes] == [
        "unchanged",
        "modified",
        "removed",
        "added",
    ]
    assert result.summary == {"added": 1, "removed": 1, "modified": 1, "unchanged": 1}


def test_empty_alignment():
    result = compare_aligned_units(
        AlignmentResult(matched_pairs=[], added_units=[], removed_units=[])
    )

    assert result.changes == []
    assert result.summary == {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
