from __future__ import annotations

from dataclasses import dataclass, field
import difflib

from src.engine.representation_model import ComparableUnit


@dataclass(frozen=True)
class SequenceAlignmentBlock:
    op_type: str
    units_a: list[ComparableUnit] = field(default_factory=list)
    units_b: list[ComparableUnit] = field(default_factory=list)


@dataclass(frozen=True)
class SequenceAlignmentResult:
    blocks: list[SequenceAlignmentBlock] = field(default_factory=list)


def _alignment_key(unit: ComparableUnit) -> str:
    if unit.canonical_label is not None:
        return unit.canonical_label
    return str(unit.payload)



def align_unit_sequences(
    units_a: list[ComparableUnit],
    units_b: list[ComparableUnit],
) -> SequenceAlignmentResult:
    keys_a = [_alignment_key(unit) for unit in units_a]
    keys_b = [_alignment_key(unit) for unit in units_b]

    matcher = difflib.SequenceMatcher(None, keys_a, keys_b)
    blocks: list[SequenceAlignmentBlock] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        blocks.append(
            SequenceAlignmentBlock(
                op_type=tag,
                units_a=units_a[i1:i2],
                units_b=units_b[j1:j2],
            )
        )

    return SequenceAlignmentResult(blocks=blocks)
