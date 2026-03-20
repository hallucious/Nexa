from __future__ import annotations

from src.engine.diff_types import DiffResult, UnitDiff
from src.engine.unit_alignment import SequenceAlignmentResult


def compare_aligned_unit_sequences(alignment: SequenceAlignmentResult) -> DiffResult:
    unit_diffs: list[UnitDiff] = []
    unchanged = 0
    changed = 0
    added = 0
    removed = 0

    for block in alignment.blocks:
        if block.op_type == "equal":
            for unit in block.units_a:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="unchanged",
                        delta=None,
                        metadata={"unit_id": unit.unit_id},
                    )
                )
                unchanged += 1
        elif block.op_type == "delete":
            for unit in block.units_a:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="removed",
                        delta=str(unit.payload),
                        metadata={"unit_id": unit.unit_id},
                    )
                )
                removed += 1
        elif block.op_type == "insert":
            for unit in block.units_b:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="added",
                        delta=str(unit.payload),
                        metadata={"unit_id": unit.unit_id},
                    )
                )
                added += 1
        elif block.op_type == "replace":
            for unit in block.units_a:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="removed",
                        delta=str(unit.payload),
                        metadata={"unit_id": unit.unit_id},
                    )
                )
                removed += 1
            for unit in block.units_b:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="added",
                        delta=str(unit.payload),
                        metadata={"unit_id": unit.unit_id},
                    )
                )
                added += 1
        else:
            raise ValueError(f"Unsupported alignment op_type: {block.op_type}")

    return DiffResult(
        unit_diffs=unit_diffs,
        summary={
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged": unchanged,
        },
        metrics={"total_units": len(unit_diffs)},
    )
