from dataclasses import dataclass
from typing import List

from src.engine.change_signal_aggregator import AggregatedChangeSignal

LABEL_UNIT_REPLACED = "UNIT_REPLACED"
LABEL_UNIT_ADDED = "UNIT_ADDED"
LABEL_UNIT_REMOVED = "UNIT_REMOVED"
LABEL_UNIT_MODIFIED = "UNIT_MODIFIED"


@dataclass(frozen=True)
class SemanticLabel:
    label: str
    source: AggregatedChangeSignal


def map_to_semantic_labels(
    aggregated: List[AggregatedChangeSignal],
) -> List[SemanticLabel]:
    result: List[SemanticLabel] = []

    for item in aggregated:
        if item.signal_type == "REPLACE":
            label = LABEL_UNIT_REPLACED
        elif item.signal_type == "ADD":
            label = LABEL_UNIT_ADDED
        elif item.signal_type == "REMOVE":
            label = LABEL_UNIT_REMOVED
        else:
            label = LABEL_UNIT_MODIFIED

        result.append(SemanticLabel(label=label, source=item))

    return result
