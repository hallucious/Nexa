from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import difflib

from src.engine.alignment_engine import AlignmentResult
from src.engine.representation_model import ComparableUnit


@dataclass(frozen=True)
class DiffOp:
    op_type: str
    text: str


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


def compute_text_diff(a: str, b: str) -> List[DiffOp]:
    matcher = difflib.SequenceMatcher(None, a, b)
    ops: List[DiffOp] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            ops.append(DiffOp("equal", a[i1:i2]))
        elif tag == "replace":
            ops.append(DiffOp("delete", a[i1:i2]))
            ops.append(DiffOp("insert", b[j1:j2]))
        elif tag == "delete":
            ops.append(DiffOp("delete", a[i1:i2]))
        elif tag == "insert":
            ops.append(DiffOp("insert", b[j1:j2]))

    return ops


def compute_word_diff(a: str, b: str) -> List[DiffOp]:
    a_words = a.split()
    b_words = b.split()

    matcher = difflib.SequenceMatcher(None, a_words, b_words)
    ops: List[DiffOp] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            text = " ".join(a_words[i1:i2])
            ops.append(DiffOp("equal", text))
        elif tag == "replace":
            delete_text = " ".join(a_words[i1:i2])
            insert_text = " ".join(b_words[j1:j2])
            ops.append(DiffOp("delete", delete_text))
            ops.append(DiffOp("insert", insert_text))
        elif tag == "delete":
            text = " ".join(a_words[i1:i2])
            ops.append(DiffOp("delete", text))
        elif tag == "insert":
            text = " ".join(b_words[j1:j2])
            ops.append(DiffOp("insert", text))

    return ops


def normalize_diff_ops(ops: List[DiffOp], *, strip_outer_equal: bool = True) -> List[DiffOp]:
    if not ops:
        return []

    normalized: List[DiffOp] = []

    for op in ops:
        if not op.text:
            continue

        if normalized and normalized[-1].op_type == op.op_type:
            prev = normalized[-1]
            joiner = ""
            if prev.text and op.text and " " not in prev.text[-1:] and " " not in op.text[:1]:
                joiner = ""
            normalized[-1] = DiffOp(prev.op_type, prev.text + joiner + op.text)
        else:
            normalized.append(op)

    if strip_outer_equal:
        if normalized and normalized[0].op_type == "equal":
            normalized = normalized[1:]
        if normalized and normalized[-1].op_type == "equal":
            normalized = normalized[:-1]

    return normalized


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
                diff = compute_word_diff(unit_a.payload, unit_b.payload)
                diff = normalize_diff_ops(diff, strip_outer_equal=False)
            else:
                diff = compute_text_diff(unit_a.payload, unit_b.payload)
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
