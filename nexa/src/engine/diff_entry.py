from __future__ import annotations

from src.engine.diff_formatter import render_diff_ops
from src.engine.diff_types import DiffOp, DiffResult
from src.engine.text_extractor import (
    extract_char_representation,
    extract_word_representation,
)
from src.engine.unit_alignment import align_unit_sequences
from src.engine.unit_comparator import compare_aligned_unit_sequences


_VALID_GRANULARITIES = {"char", "word"}


def _validate_granularity(granularity: str) -> None:
    if granularity not in _VALID_GRANULARITIES:
        raise ValueError("granularity must be 'char' or 'word'")


def compute_diff_result(a: str, b: str, *, granularity: str = "char") -> DiffResult:
    _validate_granularity(granularity)

    if granularity == "char":
        rep_a = extract_char_representation(a)
        rep_b = extract_char_representation(b)
    else:
        rep_a = extract_word_representation(a)
        rep_b = extract_word_representation(b)

    alignment = align_unit_sequences(rep_a.units, rep_b.units)
    return compare_aligned_unit_sequences(alignment)


def render_text_diff(a: str, b: str, *, granularity: str = "char") -> list[DiffOp]:
    result = compute_diff_result(a, b, granularity=granularity)
    separator = " " if granularity == "word" else ""
    return render_diff_ops(result, separator=separator)
