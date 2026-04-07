"""branch_contract.py

Typed contract for State Branch / Merge (precision track, v0.1).

Canonical objects:
  - BranchStateRef      — identity of a branch
  - BranchCandidate     — a branch with its execution summary
  - MergePolicy         — declared merge strategy
  - MergeResult         — outcome of a merge decision

Design invariants:
  - Branch creation is explicit; never hidden.
  - Merge policy is mandatory before merge.
  - Discarded branches remain traceable.
  - Node-as-sole-execution-unit is NOT violated: branching is a scheduling
    boundary, not a new execution unit kind.
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class MergeStrategy:
    PICK_BEST = "pick_best"
    PICK_FIRST = "pick_first"
    HUMAN_CHOICE = "human_choice"
    CONSENSUS = "consensus"
    UNION = "union"

    _ALL = {PICK_BEST, PICK_FIRST, HUMAN_CHOICE, CONSENSUS, UNION}


class BranchStatus:
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCARDED = "discarded"
    MERGED = "merged"

    _ALL = {ACTIVE, COMPLETED, DISCARDED, MERGED}


class BranchContractError(ValueError):
    """Raised when branch/merge contract invariants are violated."""


@dataclass(frozen=True)
class BranchStateRef:
    branch_id: str
    parent_state_ref: str
    branch_reason: str
    branch_policy: str
    created_at: str
    status: str = BranchStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.branch_id:
            raise BranchContractError("branch_id must be non-empty")
        if not self.parent_state_ref:
            raise BranchContractError("parent_state_ref must be non-empty")
        if not self.branch_reason:
            raise BranchContractError("branch_reason must be non-empty")
        if self.status not in BranchStatus._ALL:
            raise BranchContractError(f"unsupported status: {self.status!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "parent_state_ref": self.parent_state_ref,
            "branch_reason": self.branch_reason,
            "branch_policy": self.branch_policy,
            "created_at": self.created_at,
            "status": self.status,
        }


@dataclass(frozen=True)
class BranchCandidate:
    branch_ref: BranchStateRef
    score: Optional[float]           # quality/confidence score; None if unevaluated
    artifact_refs: List[str]         # outputs produced in this branch
    trace_ref: Optional[str]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_ref": self.branch_ref.to_dict(),
            "score": self.score,
            "artifact_refs": list(self.artifact_refs),
            "trace_ref": self.trace_ref,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class MergePolicy:
    policy_id: str
    strategy: str
    conflict_action: str = "escalate"  # "escalate" | "pick_first" | "block"
    require_human_on_tie: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise BranchContractError("policy_id must be non-empty")
        if self.strategy not in MergeStrategy._ALL:
            raise BranchContractError(f"unsupported strategy: {self.strategy!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "strategy": self.strategy,
            "conflict_action": self.conflict_action,
            "require_human_on_tie": self.require_human_on_tie,
        }


@dataclass(frozen=True)
class MergeResult:
    merge_id: str
    selected_branch_id: Optional[str]     # None if discarded all
    discarded_branch_ids: List[str]
    merge_policy: MergePolicy
    conflict_detected: bool
    requires_human_decision: bool
    merged_artifact_refs: List[str]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merge_id": self.merge_id,
            "selected_branch_id": self.selected_branch_id,
            "discarded_branch_ids": list(self.discarded_branch_ids),
            "merge_policy": self.merge_policy.to_dict(),
            "conflict_detected": self.conflict_detected,
            "requires_human_decision": self.requires_human_decision,
            "merged_artifact_refs": list(self.merged_artifact_refs),
            "explanation": self.explanation,
        }


# ── Factory helpers ────────────────────────────────────────────────────────

def create_branch(
    *,
    parent_state_ref: str,
    branch_reason: str,
    branch_policy: str = "default",
    branch_id: Optional[str] = None,
    now: Optional[str] = None,
) -> BranchStateRef:
    return BranchStateRef(
        branch_id=branch_id or str(uuid.uuid4()),
        parent_state_ref=parent_state_ref,
        branch_reason=branch_reason,
        branch_policy=branch_policy,
        created_at=now or datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def merge_candidates(
    candidates: List[BranchCandidate],
    *,
    policy: MergePolicy,
    merge_id: Optional[str] = None,
) -> MergeResult:
    """Apply merge policy to a set of branch candidates.

    Returns a MergeResult.  Does not mutate any branch state — callers must
    persist the result.
    """
    if not candidates:
        raise BranchContractError("candidates list must not be empty for merge")

    conflict_detected = False
    requires_human = policy.strategy == MergeStrategy.HUMAN_CHOICE
    selected_branch_id: Optional[str] = None
    discarded: List[str] = []
    merged_artifacts: List[str] = []

    if policy.strategy == MergeStrategy.PICK_BEST:
        scored = [(c.score or 0.0, c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]
        rest_scores = [s for s, _ in scored[1:]]
        # Tie detection
        if rest_scores and rest_scores[0] == best_score:
            conflict_detected = True
            if policy.require_human_on_tie:
                requires_human = True
        selected_branch_id = best.branch_ref.branch_id
        discarded = [c.branch_ref.branch_id for c in candidates if c.branch_ref.branch_id != selected_branch_id]
        merged_artifacts = list(best.artifact_refs)

    elif policy.strategy == MergeStrategy.PICK_FIRST:
        best = candidates[0]
        selected_branch_id = best.branch_ref.branch_id
        discarded = [c.branch_ref.branch_id for c in candidates[1:]]
        merged_artifacts = list(best.artifact_refs)

    elif policy.strategy == MergeStrategy.HUMAN_CHOICE:
        requires_human = True
        # No selection yet; human must decide
        discarded = []

    elif policy.strategy == MergeStrategy.UNION:
        # Combine all artifacts from all branches
        for c in candidates:
            merged_artifacts.extend(c.artifact_refs)
        # No single selection in UNION
        selected_branch_id = None
        discarded = []

    elif policy.strategy == MergeStrategy.CONSENSUS:
        # Select if majority have same score rank (simplified: use PICK_BEST)
        scored = [(c.score or 0.0, c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        selected_branch_id = best.branch_ref.branch_id
        discarded = [c.branch_ref.branch_id for c in candidates if c.branch_ref.branch_id != selected_branch_id]
        merged_artifacts = list(best.artifact_refs)

    explanation = (
        f"strategy={policy.strategy}; "
        f"selected={selected_branch_id}; "
        f"discarded={len(discarded)}; "
        f"conflict={conflict_detected}; "
        f"human_required={requires_human}"
    )

    return MergeResult(
        merge_id=merge_id or str(uuid.uuid4()),
        selected_branch_id=selected_branch_id,
        discarded_branch_ids=discarded,
        merge_policy=policy,
        conflict_detected=conflict_detected,
        requires_human_decision=requires_human,
        merged_artifact_refs=merged_artifacts,
        explanation=explanation,
    )
