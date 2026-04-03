"""
paused_run_state.py

Minimal persisted pause-state contract for review-gated runs.

This model stores only the deterministic-safe resumable boundary needed to
re-enter an existing bounded restart_from_node resume path.

Design constraints:
  - Immutable (frozen dataclass).
  - Stores only deterministic-safe fields.
  - Does NOT store full mutable runtime state, full trace, or full artifact payloads.
  - Does NOT redefine Working Save / Commit Snapshot / Execution Record semantics.
  - Rejection of stale/invalid state is explicit and engine-owned.
  - UI-agnostic: no presentation surface here.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

__all__ = ["PausedRunState", "PausedRunStateError"]


class PausedRunStateError(ValueError):
    """Raised when a paused run state is invalid or stale."""


@dataclass(frozen=True)
class PausedRunState:
    """
    Minimal durable record of a paused execution.

    All fields are deterministic-safe — meaning they describe a structural
    boundary that can be verified against the circuit on resume, not ephemeral
    runtime memory that could be faked or silently stale.

    Fields
    ------
    paused_execution_id   : str
        The execution_id of the run that was paused.  Used as the stable
        identity of this paused-run object.

    paused_node_id        : str
        The node at which execution was paused (i.e. the review gate node).
        Resume must restart from this node.

    completed_node_ids    : FrozenSet[str]
        The safe resumable boundary: node IDs that were successfully completed
        before the pause.  These can be reused on resume without re-execution.

    required_revalidation : Tuple[str, ...]
        Validation phases that must be re-run before resume is allowed.

    review_required       : Dict[str, Any]
        Snapshot of the review_required payload from the pause signal.
        Stored for audit/display — not used to drive execution logic.

    created_at            : str
        ISO-8601 timestamp when this paused-run state object was created.

    paused_at             : str
        ISO-8601 timestamp of the pause event itself (same resolution as
        created_at; provided as a distinct semantic field).

    previous_execution_id : Optional[str]
        If this run was itself a resume of a prior run, the prior run's ID.
        Enables chained run linkage in events and timeline.

    source_commit_id     : Optional[str]
        Structural commit anchor for this paused run. When present, resume
        must not silently cross commit boundaries.

    structure_fingerprint : Optional[str]
        Deterministic structural fingerprint of the circuit at pause time.
        This prevents false-positive resume readiness when the current Working
        Save has drifted structurally while still pointing at the same commit.
    """

    paused_execution_id: str
    paused_node_id: str
    completed_node_ids: FrozenSet[str]
    required_revalidation: Tuple[str, ...]
    review_required: Dict[str, Any]
    created_at: str
    paused_at: str
    previous_execution_id: Optional[str] = None
    source_commit_id: Optional[str] = None
    structure_fingerprint: Optional[str] = None

    # ── Construction helpers ─────────────────────────────────────────────────

    @classmethod
    def build(
        cls,
        *,
        paused_execution_id: str,
        paused_node_id: str,
        completed_node_ids: FrozenSet[str],
        review_required: Dict[str, Any],
        required_revalidation: Tuple[str, ...] = (
            "structural_validation",
            "determinism_pre_validation",
        ),
        previous_execution_id: Optional[str] = None,
        source_commit_id: Optional[str] = None,
        structure_fingerprint: Optional[str] = None,
        now: Optional[str] = None,
    ) -> "PausedRunState":
        """
        Construct a PausedRunState with safe defaults.

        The ``completed_node_ids`` must NOT include ``paused_node_id`` —
        the paused node was not completed.
        """
        if not paused_execution_id:
            raise PausedRunStateError("paused_execution_id must be non-empty")
        if not paused_node_id:
            raise PausedRunStateError("paused_node_id must be non-empty")
        if paused_node_id in completed_node_ids:
            raise PausedRunStateError(
                f"paused_node_id '{paused_node_id}' must not appear in completed_node_ids; "
                "the paused node was not successfully completed"
            )

        ts = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        return cls(
            paused_execution_id=paused_execution_id,
            paused_node_id=paused_node_id,
            completed_node_ids=completed_node_ids,
            required_revalidation=required_revalidation,
            review_required=dict(review_required),
            created_at=ts,
            paused_at=ts,
            previous_execution_id=previous_execution_id,
            source_commit_id=source_commit_id,
            structure_fingerprint=structure_fingerprint,
        )

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_for_resume(self, circuit_nodes: List[Dict[str, Any]]) -> None:
        """
        Explicitly validate this paused-run state against the current circuit.

        Raises PausedRunStateError if the state is stale or structurally drifted.

        Rules enforced:
          1. paused_node_id must exist in the current circuit.
          2. All completed_node_ids must still exist in the current circuit.
             If any are missing the circuit has structurally drifted and
             the boundary is stale.
          3. paused_node_id must not appear in completed_node_ids.

        This is the explicit rejection contract required by the resume rules.
        """
        if not self.paused_node_id:
            raise PausedRunStateError(
                "invalid paused run state: paused_node_id is empty"
            )

        node_ids: FrozenSet[str] = frozenset(
            n.get("id") for n in circuit_nodes if n.get("id")
        )

        if self.paused_node_id not in node_ids:
            raise PausedRunStateError(
                f"stale paused run state: paused_node_id '{self.paused_node_id}' "
                f"not found in current circuit — circuit may have structurally drifted"
            )

        stale = self.completed_node_ids - node_ids
        if stale:
            raise PausedRunStateError(
                f"stale paused run state: completed nodes no longer in circuit: "
                f"{', '.join(sorted(stale))} — circuit may have structurally drifted"
            )

        if self.paused_node_id in self.completed_node_ids:
            raise PausedRunStateError(
                f"invalid paused run state: paused_node_id '{self.paused_node_id}' "
                f"appears in completed_node_ids — paused node was not completed"
            )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict (deterministic field ordering)."""
        return {
            "paused_execution_id": self.paused_execution_id,
            "paused_node_id": self.paused_node_id,
            "previous_execution_id": self.previous_execution_id,
            "completed_node_ids": sorted(self.completed_node_ids),
            "required_revalidation": list(self.required_revalidation),
            "review_required": dict(self.review_required),
            "created_at": self.created_at,
            "paused_at": self.paused_at,
            "source_commit_id": self.source_commit_id,
            "structure_fingerprint": self.structure_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PausedRunState":
        """Deserialise from a plain dict (e.g. loaded from persistent storage)."""
        try:
            return cls(
                paused_execution_id=data["paused_execution_id"],
                paused_node_id=data["paused_node_id"],
                completed_node_ids=frozenset(data.get("completed_node_ids") or []),
                required_revalidation=tuple(
                    data.get("required_revalidation")
                    or ("structural_validation", "determinism_pre_validation")
                ),
                review_required=dict(data.get("review_required") or {}),
                created_at=data["created_at"],
                paused_at=data["paused_at"],
                previous_execution_id=data.get("previous_execution_id"),
                source_commit_id=data.get("source_commit_id"),
                structure_fingerprint=data.get("structure_fingerprint"),
            )
        except KeyError as exc:
            raise PausedRunStateError(
                f"cannot deserialise PausedRunState: missing field {exc}"
            ) from exc

    # ── Resume helper ─────────────────────────────────────────────────────────

    def to_resume_request_payload(self) -> Dict[str, Any]:
        """
        Produce the __resume__ dict that CircuitRunner._extract_resume_request
        can consume.  This wires the durable boundary back into the existing
        bounded restart_from_node resume path.
        """
        return {
            "resume_from_node_id": self.paused_node_id,
            "previous_execution_id": self.paused_execution_id,
            "reason": "review_gate_resume",
            "requires_revalidation": list(self.required_revalidation),
            "source_commit_id": self.source_commit_id,
            "structure_fingerprint": self.structure_fingerprint,
        }

    def __repr__(self) -> str:
        return (
            f"PausedRunState("
            f"paused_execution_id={self.paused_execution_id!r}, "
            f"paused_node_id={self.paused_node_id!r}, "
            f"completed={sorted(self.completed_node_ids)!r}"
            f")"
        )
