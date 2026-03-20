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


def compare_aligned_units(alignment: AlignmentResult) -> UnitDiffResult:
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
            diff = compute_text_diff(unit_a.payload, unit_b.payload)
            changes.append(UnitChange("modified", unit_a, unit_b, diff))
            summary["modified"] += 1

    for unit in alignment.removed_units:
        changes.append(UnitChange("removed", unit, None, None))
        summary["removed"] += 1

    for unit in alignment.added_units:
        changes.append(UnitChange("added", None, unit, None))
        summary["added"] += 1

    return UnitDiffResult(changes=changes, summary=summary)
