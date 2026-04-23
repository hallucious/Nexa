"""human_decision_contract.py

Typed contract for Human-in-the-Loop Decision Nodes (precision track, v0.1).

Canonical objects:
  - HumanDecisionRecord
  - HumanDecisionType
  - DownstreamAction

Human decisions are append-only records.  They do not rewrite trace history.
No silent auto-approval: every HumanDecisionRecord requires an explicit decision_type.
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class HumanDecisionType:
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"
    CHOOSE_BRANCH = "choose_branch"
    CHOOSE_MERGE = "choose_merge"
    OVERRIDE_WITH_REASON = "override_with_reason"
    STOP_EXECUTION = "stop_execution"

    _ALL = {
        APPROVE, REJECT, REQUEST_REVISION,
        CHOOSE_BRANCH, CHOOSE_MERGE,
        OVERRIDE_WITH_REASON, STOP_EXECUTION,
    }


class DownstreamAction:
    CONTINUE = "continue"
    RERUN = "rerun"
    BRANCH = "branch"
    MERGE = "merge"
    STOP = "stop"
    ESCALATE = "escalate"

    _ALL = {CONTINUE, RERUN, BRANCH, MERGE, STOP, ESCALATE}


class HumanDecisionError(ValueError):
    """Raised when human decision contract invariants are violated."""


@dataclass(frozen=True)
class HumanDecisionRecord:
    """Immutable record of a human decision at a HITL gate.

    No silent auto-approval: decision_type must be set explicitly by a
    real actor (actor_ref must be non-empty).
    """
    decision_id: str
    target_ref: str
    decision_type: str
    actor_ref: str
    downstream_action: str
    trace_refs: List[str]
    timestamp: str
    rationale_text: Optional[str] = None
    selected_option_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise HumanDecisionError("decision_id must be non-empty")
        if not self.target_ref:
            raise HumanDecisionError("target_ref must be non-empty")
        if self.decision_type not in HumanDecisionType._ALL:
            raise HumanDecisionError(
                f"unsupported decision_type: {self.decision_type!r}"
            )
        if not self.actor_ref:
            raise HumanDecisionError(
                "actor_ref must be non-empty — no silent auto-approval"
            )
        if self.downstream_action not in DownstreamAction._ALL:
            raise HumanDecisionError(
                f"unsupported downstream_action: {self.downstream_action!r}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "target_ref": self.target_ref,
            "decision_type": self.decision_type,
            "actor_ref": self.actor_ref,
            "downstream_action": self.downstream_action,
            "rationale_text": self.rationale_text,
            "selected_option_ref": self.selected_option_ref,
            "timestamp": self.timestamp,
            "trace_refs": list(self.trace_refs),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanDecisionRecord":
        return cls(
            decision_id=data["decision_id"],
            target_ref=data["target_ref"],
            decision_type=data["decision_type"],
            actor_ref=data["actor_ref"],
            downstream_action=data["downstream_action"],
            timestamp=data["timestamp"],
            trace_refs=list(data.get("trace_refs") or []),
            rationale_text=data.get("rationale_text"),
            selected_option_ref=data.get("selected_option_ref"),
        )


def record_human_decision(
    *,
    target_ref: str,
    decision_type: str,
    actor_ref: str,
    downstream_action: str,
    trace_refs: Optional[List[str]] = None,
    rationale_text: Optional[str] = None,
    selected_option_ref: Optional[str] = None,
    decision_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> HumanDecisionRecord:
    """Factory for creating a HumanDecisionRecord."""
    return HumanDecisionRecord(
        decision_id=decision_id or str(uuid.uuid4()),
        target_ref=target_ref,
        decision_type=decision_type,
        actor_ref=actor_ref,
        downstream_action=downstream_action,
        trace_refs=list(trace_refs or []),
        timestamp=timestamp
        or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        rationale_text=rationale_text,
        selected_option_ref=selected_option_ref,
    )
