from src.engine.unit_diff_engine import (
    DiffOp,
    compute_text_diff,
    compute_word_diff,
    normalize_diff_ops,
    compare_aligned_units,
)
from src.engine.alignment_engine import AlignmentResult
from src.engine.representation_model import ComparableUnit


def make_unit(unit_id: str, label: str | None, payload: str) -> ComparableUnit:
    return ComparableUnit(
        unit_id=unit_id,
        unit_kind="section",
        canonical_label=label,
        payload=payload,
        metadata={},
    )


# -------------------------
# ORIGINAL TESTS (RESTORED)
# -------------------------

def test_simple_replace_emits_delete_then_insert_with_exact_text():
    ops = compute_text_diff("ramen", "sushi")

    assert ops == [
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


def test_insert_only_emits_exact_insert_text():
    ops = compute_text_diff("", "abc")

    assert ops == [
        DiffOp("insert", "abc"),
    ]


def test_delete_only_emits_exact_delete_text():
    ops = compute_text_diff("abc", "")

    assert ops == [
        DiffOp("delete", "abc"),
    ]


def test_no_change_emits_single_equal_op_with_exact_text():
    ops = compute_text_diff("same", "same")

    assert ops == [
        DiffOp("equal", "same"),
    ]


# -------------------------
# NORMALIZATION TESTS
# -------------------------

def test_merge_consecutive_ops():
    ops = [
        DiffOp("delete", "a"),
        DiffOp("delete", "b"),
    ]
    result = normalize_diff_ops(ops)
    assert result == [DiffOp("delete", "ab")]


def test_remove_empty_ops():
    ops = [
        DiffOp("equal", ""),
        DiffOp("delete", "a"),
    ]
    result = normalize_diff_ops(ops)
    assert result == [DiffOp("delete", "a")]


def test_real_diff_normalized():
    ops = compute_text_diff("I eat ramen", "I eat sushi")
    ops = normalize_diff_ops(ops)

    assert ops == [
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


# -------------------------
# COMPARE TESTS (FULL)
# -------------------------

def test_compare_units_modified_attaches_diff_and_exact_summary():
    a = make_unit("a", "x", "ramen")
    b = make_unit("b", "x", "sushi")

    alignment = AlignmentResult(
        matched_pairs=[(a, b)],
        added_units=[],
        removed_units=[],
    )

    result = compare_aligned_units(alignment)

    assert result.summary == {
        "added": 0,
        "removed": 0,
        "modified": 1,
        "unchanged": 0,
    }
    assert len(result.changes) == 1
    assert result.changes[0].change_type == "modified"
    assert result.changes[0].unit_a == a
    assert result.changes[0].unit_b == b
    assert result.changes[0].diff == [
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


def test_compare_units_unchanged_uses_diff_none_and_exact_summary():
    a = make_unit("a", "x", "same")
    b = make_unit("b", "x", "same")

    alignment = AlignmentResult(
        matched_pairs=[(a, b)],
        added_units=[],
        removed_units=[],
    )

    result = compare_aligned_units(alignment)

    assert result.summary == {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "unchanged": 1,
    }
    assert len(result.changes) == 1
    assert result.changes[0].change_type == "unchanged"
    assert result.changes[0].unit_a == a
    assert result.changes[0].unit_b == b
    assert result.changes[0].diff is None


def test_compare_units_added_removed_and_modified_mixed_summary_is_exact():
    a1 = make_unit("a1", "morning", "same")
    b1 = make_unit("b1", "morning", "same")
    a2 = make_unit("a2", "lunch", "ramen")
    b2 = make_unit("b2", "lunch", "sushi")
    a3 = make_unit("a3", "afternoon", "museum")
    b3 = make_unit("b3", "dinner", "bar")

    alignment = AlignmentResult(
        matched_pairs=[(a1, b1), (a2, b2)],
        added_units=[b3],
        removed_units=[a3],
    )

    result = compare_aligned_units(alignment)

    assert result.summary == {
        "added": 1,
        "removed": 1,
        "modified": 1,
        "unchanged": 1,
    }

    assert [change.change_type for change in result.changes] == [
        "unchanged",
        "modified",
        "removed",
        "added",
    ]

    assert result.changes[0].diff is None
    assert result.changes[1].diff == [
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]
    assert result.changes[2].unit_a == a3
    assert result.changes[2].unit_b is None
    assert result.changes[3].unit_a is None
    assert result.changes[3].unit_b == b3


def test_word_diff_basic():
    ops = compute_word_diff("I eat ramen", "I eat sushi")

    assert ops == [
        DiffOp("equal", "I eat"),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


def test_word_diff_sentence():
    ops = compute_word_diff("I eat ramen today", "I ate sushi today")

    assert ops == [
        DiffOp("equal", "I"),
        DiffOp("delete", "eat ramen"),
        DiffOp("insert", "ate sushi"),
        DiffOp("equal", "today"),
    ]


def test_char_and_word_diff_are_different():
    char_ops = normalize_diff_ops(compute_text_diff("I eat ramen", "I eat sushi"))
    word_ops = compute_word_diff("I eat ramen", "I eat sushi")
    word_ops = normalize_diff_ops(word_ops, strip_outer_equal=False)

    assert char_ops != word_ops
    assert word_ops == [
        DiffOp("equal", "I eat"),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


def test_compare_units_word_mode():
    a = make_unit("a", "x", "I eat ramen")
    b = make_unit("b", "x", "I eat sushi")

    alignment = AlignmentResult(
        matched_pairs=[(a, b)],
        added_units=[],
        removed_units=[],
    )

    result = compare_aligned_units(alignment, mode="word")

    assert result.changes[0].diff == [
        DiffOp("equal", "I eat"),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]
