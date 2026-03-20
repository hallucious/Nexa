from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from src.engine.representation_model import ComparableUnit


@dataclass(frozen=True)
class AlignmentResult:
    matched_pairs: List[Tuple[ComparableUnit, ComparableUnit]]
    added_units: List[ComparableUnit]
    removed_units: List[ComparableUnit]


def align_units(
    units_a: List[ComparableUnit],
    units_b: List[ComparableUnit],
) -> AlignmentResult:
    """
    Deterministically align ComparableUnit sequences.

    Strategy:
    1. Exact canonical_label match, preserving order of appearance.
    2. Fallback positional matching for remaining unmatched units.
    3. Leftover A units are removed; leftover B units are added.
    """
    unmatched_a = list(units_a)
    unmatched_b = list(units_b)

    matched_pairs: List[Tuple[ComparableUnit, ComparableUnit]] = []

    # Step 1: exact canonical_label matching in order of appearance
    label_matched_a_ids: set[str] = set()
    label_matched_b_ids: set[str] = set()

    for unit_a in units_a:
        if unit_a.canonical_label is None:
            continue
        for unit_b in units_b:
            if unit_b.canonical_label is None:
                continue
            if unit_a.unit_id in label_matched_a_ids:
                break
            if unit_b.unit_id in label_matched_b_ids:
                continue
            if unit_a.canonical_label == unit_b.canonical_label:
                matched_pairs.append((unit_a, unit_b))
                label_matched_a_ids.add(unit_a.unit_id)
                label_matched_b_ids.add(unit_b.unit_id)
                break

    unmatched_a = [u for u in units_a if u.unit_id not in label_matched_a_ids]
    unmatched_b = [u for u in units_b if u.unit_id not in label_matched_b_ids]

    # Step 2: fallback positional matching
    fallback_count = min(len(unmatched_a), len(unmatched_b))
    for idx in range(fallback_count):
        matched_pairs.append((unmatched_a[idx], unmatched_b[idx]))

    # Step 3: leftovers
    removed_units = unmatched_a[fallback_count:]
    added_units = unmatched_b[fallback_count:]

    return AlignmentResult(
        matched_pairs=matched_pairs,
        added_units=added_units,
        removed_units=removed_units,
    )
