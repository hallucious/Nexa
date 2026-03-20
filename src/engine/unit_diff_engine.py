from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from src.engine.alignment_engine import AlignmentResult
from src.engine.diff_formatter import render_diff_ops
from src.engine.diff_types import DiffOp
from src.engine.representation_model import ComparableUnit
from src.engine.text_extractor import extract_char_representation, extract_word_representation
from src.engine.unit_alignment import align_unit_sequences
from src.engine.unit_comparator import compare_aligned_unit_sequences


@dataclass(frozen=True)
class UnitChange:
    change_type: str
    unit_a: Optional[ComparableUnit]
    unit_b: Optional[ComparableUnit]
    diff: Optional[List[DiffOp]] = None


@dataclass(frozen=True)
class UnitDiffResult:
    changes: List[UnitChange]
    summary: dict


def _ops_from_representations(a: str, b: str, *, mode: str) -> List[DiffOp]:
    if mode == "char":
        rep_a = extract_char_representation(a)
        rep_b = extract_char_representation(b)
    elif mode == "word":
        rep_a = extract_word_representation(a)
        rep_b = extract_word_representation(b)
    else:
        raise ValueError("mode must be 'char' or 'word'")

    alignment = align_unit_sequences(rep_a.units, rep_b.units)
    diff_result = compare_aligned_unit_sequences(alignment)
    return render_diff_ops(diff_result)


def _normalize_diff_ops(
    ops: List[DiffOp], *, separator: str, strip_outer_equal: bool = True
) -> List[DiffOp]:
    if not ops:
        return []

    normalized: List[DiffOp] = []

    for op in ops:
        if not op.text:
            continue

        if normalized and normalized[-1].op_type == op.op_type:
            prev = normalized[-1]
            normalized[-1] = DiffOp(prev.op_type, prev.text + separator + op.text)
        else:
            normalized.append(op)

    if strip_outer_equal:
        if normalized and normalized[0].op_type == "equal":
            normalized = normalized[1:]
        if normalized and normalized[-1].op_type == "equal":
            normalized = normalized[:-1]

    return normalized


def normalize_diff_ops(ops: List[DiffOp], *, strip_outer_equal: bool = True) -> List[DiffOp]:
    separator = ""
    if any(" " in op.text for op in ops):
        separator = " "
    return _normalize_diff_ops(ops, separator=separator, strip_outer_equal=strip_outer_equal)


def compute_text_diff(a: str, b: str) -> List[DiffOp]:
    raw_ops = _ops_from_representations(a, b, mode="char")
    return _normalize_diff_ops(raw_ops, separator="", strip_outer_equal=False)


def compute_word_diff(a: str, b: str) -> List[DiffOp]:
    raw_ops = _ops_from_representations(a, b, mode="word")
    return _normalize_diff_ops(raw_ops, separator=" ", strip_outer_equal=False)


def compare_aligned_units(alignment: AlignmentResult, mode: str = "char") -> UnitDiffResult:
    if mode not in {"char", "word"}:
        raise ValueError("mode must be 'char' or 'word'")

    changes: List[UnitChange] = []

    summary = {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "unchanged": 0,
    }

    for unit_a, unit_b in alignment.matched_pairs:
        if unit_a.payload == unit_b.payload:
            changes.append(UnitChange("unchanged", unit_a, unit_b, None))
            summary["unchanged"] += 1
        else:
            if mode == "word":
                diff = compute_word_diff(str(unit_a.payload), str(unit_b.payload))
                diff = normalize_diff_ops(diff, strip_outer_equal=False)
            else:
                diff = compute_text_diff(str(unit_a.payload), str(unit_b.payload))
                diff = normalize_diff_ops(diff)
            changes.append(UnitChange("modified", unit_a, unit_b, diff))
            summary["modified"] += 1

    for unit in alignment.removed_units:
        changes.append(UnitChange("removed", unit, None, None))
        summary["removed"] += 1

    for unit in alignment.added_units:
        changes.append(UnitChange("added", None, unit, None))
        summary["added"] += 1

    return UnitDiffResult(changes=changes, summary=summary)
