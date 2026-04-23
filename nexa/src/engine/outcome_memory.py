"""outcome_memory.py

Outcome Learning Memory (precision track, v0.1).

Stores reusable success/failure pattern summaries from prior executions.
Memory is updated after execution cycles — never during live execution.
Memory suggestions are deterministic and explainable; no self-modification.

Pattern families:
  - SuccessPattern   — good route/verifier/prompt combos
  - FailurePattern   — repeated failure clusters and reason_codes
  - RepairPattern    — what fixes worked for what problem class
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class MemoryFamily:
    SUCCESS = "success"
    FAILURE = "failure"
    REPAIR = "repair"

    _ALL = {SUCCESS, FAILURE, REPAIR}


class OutcomeMemoryError(ValueError):
    """Raised when outcome memory contract invariants are violated."""


# ── Pattern types ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SuccessPattern:
    pattern_id: str
    family: str
    route_tier: str
    provider_id: str
    task_types: List[str]
    confidence_score: float
    verifier_ids: List[str]
    trace_refs: List[str]
    recorded_at: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "family": self.family,
            "route_tier": self.route_tier,
            "provider_id": self.provider_id,
            "task_types": list(self.task_types),
            "confidence_score": self.confidence_score,
            "verifier_ids": list(self.verifier_ids),
            "trace_refs": list(self.trace_refs),
            "recorded_at": self.recorded_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FailurePattern:
    pattern_id: str
    family: str
    reason_codes: List[str]
    task_types: List[str]
    occurrence_count: int
    provider_ids: List[str]
    trace_refs: List[str]
    recorded_at: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "family": self.family,
            "reason_codes": list(self.reason_codes),
            "task_types": list(self.task_types),
            "occurrence_count": self.occurrence_count,
            "provider_ids": list(self.provider_ids),
            "trace_refs": list(self.trace_refs),
            "recorded_at": self.recorded_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RepairPattern:
    pattern_id: str
    family: str
    problem_reason_codes: List[str]
    repair_action: str
    success_rate: float   # 0.0–1.0
    task_types: List[str]
    trace_refs: List[str]
    recorded_at: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "family": self.family,
            "problem_reason_codes": list(self.problem_reason_codes),
            "repair_action": self.repair_action,
            "success_rate": self.success_rate,
            "task_types": list(self.task_types),
            "trace_refs": list(self.trace_refs),
            "recorded_at": self.recorded_at,
            "notes": self.notes,
        }


# ── Memory store ───────────────────────────────────────────────────────────

class OutcomeMemoryStore:
    """Bounded in-memory store for outcome patterns.

    Append-only per pattern_id; no silent overwrite.
    Query interface: by reason_code, task_type, family.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self._success: Dict[str, SuccessPattern] = {}
        self._failure: Dict[str, FailurePattern] = {}
        self._repair: Dict[str, RepairPattern] = {}
        self._max = max_entries

    def _total(self) -> int:
        return len(self._success) + len(self._failure) + len(self._repair)

    def _check_capacity(self) -> None:
        if self._total() >= self._max:
            raise OutcomeMemoryError(
                f"OutcomeMemoryStore capacity ({self._max}) reached"
            )

    def record_success(self, pattern: SuccessPattern) -> None:
        if pattern.pattern_id in self._success:
            raise OutcomeMemoryError(
                f"duplicate success pattern_id: {pattern.pattern_id!r}"
            )
        self._check_capacity()
        self._success[pattern.pattern_id] = pattern

    def record_failure(self, pattern: FailurePattern) -> None:
        if pattern.pattern_id in self._failure:
            raise OutcomeMemoryError(
                f"duplicate failure pattern_id: {pattern.pattern_id!r}"
            )
        self._check_capacity()
        self._failure[pattern.pattern_id] = pattern

    def record_repair(self, pattern: RepairPattern) -> None:
        if pattern.pattern_id in self._repair:
            raise OutcomeMemoryError(
                f"duplicate repair pattern_id: {pattern.pattern_id!r}"
            )
        self._check_capacity()
        self._repair[pattern.pattern_id] = pattern

    # ── Query interface ────────────────────────────────────────────────────

    def query_failures_by_reason_code(
        self, reason_code: str
    ) -> List[FailurePattern]:
        return [
            p for p in self._failure.values()
            if reason_code in p.reason_codes
        ]

    def query_successes_by_task_type(
        self, task_type: str
    ) -> List[SuccessPattern]:
        return [
            p for p in self._success.values()
            if task_type in p.task_types
        ]

    def query_repairs_by_reason_code(
        self, reason_code: str
    ) -> List[RepairPattern]:
        return [
            p for p in self._repair.values()
            if reason_code in p.problem_reason_codes
        ]

    def suggest_route_tier(self, task_type: str) -> Optional[str]:
        """Return the route_tier from the highest-confidence success pattern
        for a given task_type.  Returns None if no data available.
        """
        candidates = self.query_successes_by_task_type(task_type)
        if not candidates:
            return None
        best = max(candidates, key=lambda p: p.confidence_score)
        return best.route_tier

    def total_entries(self) -> int:
        return self._total()

    def all_families_summary(self) -> Dict[str, int]:
        return {
            MemoryFamily.SUCCESS: len(self._success),
            MemoryFamily.FAILURE: len(self._failure),
            MemoryFamily.REPAIR: len(self._repair),
        }


# ── Factory helpers ────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record_success_pattern(
    store: OutcomeMemoryStore,
    *,
    route_tier: str,
    provider_id: str,
    task_types: List[str],
    confidence_score: float,
    verifier_ids: Optional[List[str]] = None,
    trace_refs: Optional[List[str]] = None,
    notes: str = "",
    pattern_id: Optional[str] = None,
) -> SuccessPattern:
    p = SuccessPattern(
        pattern_id=pattern_id or str(uuid.uuid4()),
        family=MemoryFamily.SUCCESS,
        route_tier=route_tier,
        provider_id=provider_id,
        task_types=list(task_types),
        confidence_score=confidence_score,
        verifier_ids=list(verifier_ids or []),
        trace_refs=list(trace_refs or []),
        recorded_at=_now(),
        notes=notes,
    )
    store.record_success(p)
    return p


def record_failure_pattern(
    store: OutcomeMemoryStore,
    *,
    reason_codes: List[str],
    task_types: List[str],
    occurrence_count: int = 1,
    provider_ids: Optional[List[str]] = None,
    trace_refs: Optional[List[str]] = None,
    notes: str = "",
    pattern_id: Optional[str] = None,
) -> FailurePattern:
    p = FailurePattern(
        pattern_id=pattern_id or str(uuid.uuid4()),
        family=MemoryFamily.FAILURE,
        reason_codes=list(reason_codes),
        task_types=list(task_types),
        occurrence_count=occurrence_count,
        provider_ids=list(provider_ids or []),
        trace_refs=list(trace_refs or []),
        recorded_at=_now(),
        notes=notes,
    )
    store.record_failure(p)
    return p


def record_repair_pattern(
    store: OutcomeMemoryStore,
    *,
    problem_reason_codes: List[str],
    repair_action: str,
    success_rate: float,
    task_types: List[str],
    trace_refs: Optional[List[str]] = None,
    notes: str = "",
    pattern_id: Optional[str] = None,
) -> RepairPattern:
    p = RepairPattern(
        pattern_id=pattern_id or str(uuid.uuid4()),
        family=MemoryFamily.REPAIR,
        problem_reason_codes=list(problem_reason_codes),
        repair_action=repair_action,
        success_rate=success_rate,
        task_types=list(task_types),
        trace_refs=list(trace_refs or []),
        recorded_at=_now(),
        notes=notes,
    )
    store.record_repair(p)
    return p
