from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from src.engine.unit_diff_engine import DiffOp


@dataclass(frozen=True)
class ChangeSignal:
    signal_type: str
    before: Optional[str]
    after: Optional[str]


_VALID_SIGNAL_TYPES = {"REPLACE", "ADD", "REMOVE"}


def _build_signal(signal_type: str, *, before: Optional[str], after: Optional[str]) -> ChangeSignal:
    if signal_type not in _VALID_SIGNAL_TYPES:
        raise ValueError(f"Unsupported signal_type: {signal_type}")
    return ChangeSignal(signal_type=signal_type, before=before, after=after)


def extract_change_signals(diff_ops: List[DiffOp]) -> List[ChangeSignal]:
    signals: List[ChangeSignal] = []
    index = 0

    while index < len(diff_ops):
        current = diff_ops[index]

        if current.op_type == "equal":
            index += 1
            continue

        if current.op_type == "delete":
            next_index = index + 1
            if next_index < len(diff_ops) and diff_ops[next_index].op_type == "insert":
                signals.append(
                    _build_signal(
                        "REPLACE",
                        before=current.text,
                        after=diff_ops[next_index].text,
                    )
                )
                index += 2
                continue

            signals.append(_build_signal("REMOVE", before=current.text, after=None))
            index += 1
            continue

        if current.op_type == "insert":
            signals.append(_build_signal("ADD", before=None, after=current.text))
            index += 1
            continue

        raise ValueError(f"Unsupported diff op_type: {current.op_type}")

    return signals
