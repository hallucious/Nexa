from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from src.engine.change_signal_extractor import ChangeSignal

AGGREGATED_SIGNAL_REPLACE = "REPLACE"
AGGREGATED_SIGNAL_ADD = "ADD"
AGGREGATED_SIGNAL_REMOVE = "REMOVE"
AGGREGATED_SIGNAL_MIXED = "MIXED"


@dataclass(frozen=True)
class AggregatedChangeSignal:
    signal_type: str
    before: Optional[str]
    after: Optional[str]
    source_signals: Sequence[ChangeSignal]


def _join_parts(parts: List[str]) -> Optional[str]:
    cleaned = [part for part in parts if part]
    if not cleaned:
        return None
    return " ".join(cleaned)


def _finalize_run(run: List[ChangeSignal]) -> AggregatedChangeSignal:
    signal_types = {signal.signal_type for signal in run}
    signal_type = run[0].signal_type if len(signal_types) == 1 else AGGREGATED_SIGNAL_MIXED

    before = _join_parts([signal.before for signal in run if signal.before])
    after = _join_parts([signal.after for signal in run if signal.after])

    return AggregatedChangeSignal(
        signal_type=signal_type,
        before=before,
        after=after,
        source_signals=tuple(run),
    )


def _can_extend_run(run: List[ChangeSignal], signal: ChangeSignal) -> bool:
    run_types = {item.signal_type for item in run}

    if len(run_types) == 1 and signal.signal_type in run_types:
        return True

    if run_types == {AGGREGATED_SIGNAL_REPLACE} and signal.signal_type in {
        AGGREGATED_SIGNAL_ADD,
        AGGREGATED_SIGNAL_REMOVE,
    }:
        return True

    return False


def aggregate_change_signals(signals: List[ChangeSignal]) -> List[AggregatedChangeSignal]:
    if not signals:
        return []

    aggregated: List[AggregatedChangeSignal] = []
    run: List[ChangeSignal] = [signals[0]]

    for signal in signals[1:]:
        if _can_extend_run(run, signal):
            run.append(signal)
            continue

        aggregated.append(_finalize_run(run))
        run = [signal]

    aggregated.append(_finalize_run(run))
    return aggregated
