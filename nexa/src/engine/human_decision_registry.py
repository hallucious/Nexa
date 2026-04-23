"""human_decision_registry.py

In-memory registry for Human-in-the-Loop decision records.

Stores HumanDecisionRecord entries keyed by decision_id.
Append-only: existing records are never modified.
Query by target_ref or decision_type for audit / trace integration.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from src.contracts.human_decision_contract import (
    HumanDecisionRecord,
    HumanDecisionError,
)


class HumanDecisionRegistry:
    """Thread-unsafe in-process registry.

    For persistent storage, serialize records via .to_dict() / .from_dict().
    """

    def __init__(self) -> None:
        self._records: Dict[str, HumanDecisionRecord] = {}

    def register(self, record: HumanDecisionRecord) -> None:
        """Append a decision record.  Raises HumanDecisionError on duplicate."""
        if record.decision_id in self._records:
            raise HumanDecisionError(
                f"duplicate decision_id: {record.decision_id!r}"
            )
        self._records[record.decision_id] = record

    def get(self, decision_id: str) -> Optional[HumanDecisionRecord]:
        return self._records.get(decision_id)

    def all_records(self) -> List[HumanDecisionRecord]:
        return list(self._records.values())

    def by_target(self, target_ref: str) -> List[HumanDecisionRecord]:
        return [r for r in self._records.values() if r.target_ref == target_ref]

    def by_type(self, decision_type: str) -> List[HumanDecisionRecord]:
        return [r for r in self._records.values() if r.decision_type == decision_type]

    def pending_reviews(self, target_ref: Optional[str] = None) -> List[HumanDecisionRecord]:
        """Return records that resulted in a downstream 'escalate' or 'rerun'."""
        pending = [
            r for r in self._records.values()
            if r.downstream_action in ("escalate", "rerun")
        ]
        if target_ref:
            pending = [r for r in pending if r.target_ref == target_ref]
        return pending

    def count(self) -> int:
        return len(self._records)
