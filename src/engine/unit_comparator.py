from __future__ import annotations

from src.engine.diff_types import DiffResult, UnitDiff
from src.engine.unit_alignment import SequenceAlignmentResult


def compare_aligned_unit_sequences(alignment: SequenceAlignmentResult) -> DiffResult:
    unit_diffs: list[UnitDiff] = []

    for block in alignment.blocks:
        if block.op_type == "equal":
            for unit in block.units_a:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="unchanged",
                        unit=unit,
                        metadata={"source": "a"},
                    )
                )
        elif block.op_type == "delete":
            for unit in block.units_a:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="removed",
                        unit=unit,
                        metadata={"source": "a"},
                    )
                )
        elif block.op_type == "insert":
            for unit in block.units_b:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="added",
                        unit=unit,
                        metadata={"source": "b"},
                    )
                )
        elif block.op_type == "replace":
            for unit in block.units_a:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="removed",
                        unit=unit,
                        metadata={"source": "a"},
                    )
                )
            for unit in block.units_b:
                unit_diffs.append(
                    UnitDiff(
                        unit_kind=unit.unit_kind,
                        label=unit.canonical_label,
                        status="added",
                        unit=unit,
                        metadata={"source": "b"},
                    )
                )
        else:
            raise ValueError(f"Unsupported alignment op_type: {block.op_type}")

    summary = {
        "added": sum(1 for item in unit_diffs if item.status == "added"),
        "removed": sum(1 for item in unit_diffs if item.status == "removed"),
        "unchanged": sum(1 for item in unit_diffs if item.status == "unchanged"),
    }
    metrics = {"unit_count": len(unit_diffs)}
    return DiffResult(unit_diffs=unit_diffs, summary=summary, metrics=metrics)
