from dataclasses import dataclass
from typing import List

from src.engine.change_signal_aggregator import AggregatedChangeSignal

LABEL_CONTENT_REPLACED = "CONTENT_REPLACED"
LABEL_CONTENT_ADDED = "CONTENT_ADDED"
LABEL_CONTENT_REMOVED = "CONTENT_REMOVED"
LABEL_CONTENT_MODIFIED = "CONTENT_MODIFIED"


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
            label = LABEL_CONTENT_REPLACED
        elif item.signal_type == "ADD":
            label = LABEL_CONTENT_ADDED
        elif item.signal_type == "REMOVE":
            label = LABEL_CONTENT_REMOVED
        else:
            label = LABEL_CONTENT_MODIFIED

        result.append(SemanticLabel(label=label, source=item))

    return result
