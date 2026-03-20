from __future__ import annotations

from dataclasses import dataclass, field

from src.engine.alignment_engine import AlignmentResult
from src.engine.representation_model import ComparableUnit


@dataclass(frozen=True)
class UnitChange:
    """Single unit-level change classification result."""

    change_type: str
    unit_a: ComparableUnit | None
    unit_b: ComparableUnit | None


@dataclass(frozen=True)
class UnitDiffResult:
    """Aggregate result for unit-level comparison over an alignment."""

    changes: list[UnitChange] = field(default_factory=list)
    summary: dict[str, int] = field(
        default_factory=lambda: {
            "added": 0,
            "removed": 0,
            "modified": 0,
            "unchanged": 0,
        }
    )


_ALLOWED_CHANGE_TYPES = {"added", "removed", "modified", "unchanged"}


def _empty_summary() -> dict[str, int]:
    return {
        "added": 0,
        "removed": 0,
        "modified": 0,
        "unchanged": 0,
    }


def _make_change(
    *,
    change_type: str,
    unit_a: ComparableUnit | None,
    unit_b: ComparableUnit | None,
) -> UnitChange:
    if change_type not in _ALLOWED_CHANGE_TYPES:
        raise ValueError(f"unsupported change_type: {change_type}")
    return UnitChange(change_type=change_type, unit_a=unit_a, unit_b=unit_b)


def compare_aligned_units(alignment: AlignmentResult) -> UnitDiffResult:
    """Classify aligned ComparableUnits into deterministic unit-level changes.

    Rules:
    - matched pair with equal payload -> unchanged
    - matched pair with different payload -> modified
    - removed_units -> removed
    - added_units -> added
    """

    changes: list[UnitChange] = []
    summary = _empty_summary()

    for unit_a, unit_b in alignment.matched_pairs:
        if unit_a.payload == unit_b.payload:
            change = _make_change(
                change_type="unchanged",
                unit_a=unit_a,
                unit_b=unit_b,
            )
            summary["unchanged"] += 1
        else:
            change = _make_change(
                change_type="modified",
                unit_a=unit_a,
                unit_b=unit_b,
            )
            summary["modified"] += 1
        changes.append(change)

    for unit in alignment.removed_units:
        changes.append(
            _make_change(
                change_type="removed",
                unit_a=unit,
                unit_b=None,
            )
        )
        summary["removed"] += 1

    for unit in alignment.added_units:
        changes.append(
            _make_change(
                change_type="added",
                unit_a=None,
                unit_b=unit,
            )
        )
        summary["added"] += 1

    return UnitDiffResult(changes=changes, summary=summary)
