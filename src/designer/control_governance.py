from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.designer.models.designer_session_state_card import RevisionAttemptSummary

_RECENT_ATTEMPT_LIMIT = 3
_REPEAT_CONFIRMATION_THRESHOLD = 2

_GOVERNANCE_NOTE_KEYS = frozenset(
    {
        "control_governance_applied",
        "control_governance_recent_attempts",
        "control_governance_recent_attempt_count",
        "control_governance_repeat_reason_code",
        "control_governance_repeat_reason_count",
        "control_governance_repeat_stage",
        "control_governance_repeat_outcome",
        "control_governance_confirmation_loop_count",
        "control_governance_interpretation_safety_mode",
        "control_governance_requires_explicit_referential_anchor",
        "control_governance_referential_anchor_policy",
        "control_governance_referential_anchor_examples",
    }
)


def apply_control_governance_notes(
    notes: Mapping[str, Any],
    attempt_history: Sequence[RevisionAttemptSummary],
) -> dict[str, Any]:
    next_notes = {
        key: value
        for key, value in dict(notes).items()
        if key not in _GOVERNANCE_NOTE_KEYS
    }
    if not attempt_history:
        return next_notes

    recent_attempts = list(attempt_history[-_RECENT_ATTEMPT_LIMIT:])
    latest = recent_attempts[-1]
    repeated_reason_count = _trailing_repeat_count(
        recent_attempts,
        predicate=lambda item: item.reason_code == latest.reason_code,
    )
    confirmation_loop_count = _trailing_repeat_count(
        recent_attempts,
        predicate=lambda item: item.outcome == "confirmation_required",
    )
    strict_referential_anchor = confirmation_loop_count >= _REPEAT_CONFIRMATION_THRESHOLD

    next_notes.update(
        {
            "control_governance_applied": True,
            "control_governance_recent_attempts": [
                {
                    "attempt_index": item.attempt_index,
                    "stage": item.stage,
                    "outcome": item.outcome,
                    "reason_code": item.reason_code,
                    "message": item.message,
                }
                for item in recent_attempts
            ],
            "control_governance_recent_attempt_count": len(recent_attempts),
            "control_governance_repeat_reason_code": latest.reason_code,
            "control_governance_repeat_reason_count": repeated_reason_count,
            "control_governance_repeat_stage": latest.stage,
            "control_governance_repeat_outcome": latest.outcome,
            "control_governance_confirmation_loop_count": confirmation_loop_count,
            "control_governance_interpretation_safety_mode": (
                "explicit_referential_anchor_required"
                if strict_referential_anchor
                else "standard"
            ),
            "control_governance_requires_explicit_referential_anchor": strict_referential_anchor,
            "control_governance_referential_anchor_policy": (
                "after repeated confirmation cycles, referential requests should include an explicit commit anchor, an explicit node target, or an explicit non-latest selector before auto-resolution resumes"
            ),
            "control_governance_referential_anchor_examples": [
                "Rollback commit abc1234",
                "Undo the last change on node reviewer",
                "Revert the change before last",
            ],
        }
    )
    return next_notes


def requires_explicit_referential_anchor(notes: Mapping[str, Any]) -> bool:
    return bool(notes.get("control_governance_requires_explicit_referential_anchor"))


def _trailing_repeat_count(
    items: Sequence[RevisionAttemptSummary],
    *,
    predicate,
) -> int:
    count = 0
    for item in reversed(items):
        if not predicate(item):
            break
        count += 1
    return count
