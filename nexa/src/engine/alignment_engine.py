from __future__ import annotations

from dataclasses import dataclass, field

from src.engine.representation_model import ComparableUnit


@dataclass(frozen=True)
class AlignmentResult:
    """Deterministic correspondence result between two ComparableUnit lists."""

    matched_pairs: list[tuple[ComparableUnit, ComparableUnit]] = field(default_factory=list)
    added_units: list[ComparableUnit] = field(default_factory=list)
    removed_units: list[ComparableUnit] = field(default_factory=list)


def align_units(
    units_a: list[ComparableUnit],
    units_b: list[ComparableUnit],
) -> AlignmentResult:
    """Align ComparableUnits deterministically.

    Matching strategy:
    1. Exact canonical_label match, preserving order of appearance.
    2. Positional fallback for remaining unmatched units.
    3. Any leftover A units are removed; leftover B units are added.
    """

    matched_pairs: list[tuple[ComparableUnit, ComparableUnit]] = []
    matched_a_indices: set[int] = set()
    matched_b_indices: set[int] = set()

    # Step 1: exact canonical_label matching in order of appearance.
    for a_index, unit_a in enumerate(units_a):
        if unit_a.canonical_label is None or a_index in matched_a_indices:
            continue
        for b_index, unit_b in enumerate(units_b):
            if b_index in matched_b_indices or unit_b.canonical_label is None:
                continue
            if unit_a.canonical_label == unit_b.canonical_label:
                matched_pairs.append((unit_a, unit_b))
                matched_a_indices.add(a_index)
                matched_b_indices.add(b_index)
                break

    remaining_a = [
        unit for index, unit in enumerate(units_a) if index not in matched_a_indices
    ]
    remaining_b = [
        unit for index, unit in enumerate(units_b) if index not in matched_b_indices
    ]

    # Step 2: positional fallback for remaining unmatched units.
    fallback_count = min(len(remaining_a), len(remaining_b))
    for index in range(fallback_count):
        matched_pairs.append((remaining_a[index], remaining_b[index]))

    removed_units = remaining_a[fallback_count:]
    added_units = remaining_b[fallback_count:]

    return AlignmentResult(
        matched_pairs=matched_pairs,
        added_units=added_units,
        removed_units=removed_units,
    )
