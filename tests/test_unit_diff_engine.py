from src.engine.diff_entry import compute_diff_result, render_text_diff
from src.engine.diff_types import DiffOp, DiffResult


def test_compute_diff_result_replace_summary_char():
    result = compute_diff_result("ramen", "sushi", granularity="char")

    assert isinstance(result, DiffResult)
    assert result.summary == {
        "added": 5,
        "removed": 5,
        "changed": 0,
        "unchanged": 0,
    }


def test_render_text_diff_insert_only():
    ops = render_text_diff("", "abc", granularity="char")

    assert ops == [
        DiffOp("insert", "abc"),
    ]


def test_render_text_diff_delete_only():
    ops = render_text_diff("abc", "", granularity="char")

    assert ops == [
        DiffOp("delete", "abc"),
    ]


def test_render_text_diff_unchanged_single_equal():
    ops = render_text_diff("same", "same", granularity="char")

    assert ops == [
        DiffOp("equal", "same"),
    ]


def test_render_text_diff_real_diff_normalized_by_formatter():
    ops = render_text_diff("I eat ramen", "I eat sushi", granularity="char")

    assert ops == [
        DiffOp("equal", "I eat "),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


def test_word_diff_basic_phrase_grouping():
    ops = render_text_diff("I eat ramen", "I eat sushi", granularity="word")

    assert ops == [
        DiffOp("equal", "I eat"),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]


def test_word_diff_sentence_grouping():
    ops = render_text_diff("I eat ramen today", "I ate sushi today", granularity="word")

    assert ops == [
        DiffOp("equal", "I"),
        DiffOp("delete", "eat ramen"),
        DiffOp("insert", "ate sushi"),
        DiffOp("equal", "today"),
    ]


def test_char_and_word_diff_are_different():
    char_ops = render_text_diff("I eat ramen", "I eat sushi", granularity="char")
    word_ops = render_text_diff("I eat ramen", "I eat sushi", granularity="word")

    assert char_ops != word_ops
    assert word_ops == [
        DiffOp("equal", "I eat"),
        DiffOp("delete", "ramen"),
        DiffOp("insert", "sushi"),
    ]
