from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
        "control_governance_policy_tier",
        "control_governance_policy_reason",
        "control_governance_precheck_message",
        "control_governance_preview_hint",
        "control_governance_next_actions",
    }
)


@dataclass(frozen=True)
class ControlGovernancePolicy:
    tier: str = "standard"
    interpretation_safety_mode: str = "standard"
    requires_explicit_referential_anchor: bool = False
    reason: str = "No repeated confirmation-governance escalation is currently active."
    precheck_message: str = ""
    preview_hint: str = ""
    next_actions: tuple[str, ...] = ()


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
    policy = _derive_control_governance_policy(
        repeated_reason_count=repeated_reason_count,
        confirmation_loop_count=confirmation_loop_count,
    )

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
            "control_governance_interpretation_safety_mode": policy.interpretation_safety_mode,
            "control_governance_requires_explicit_referential_anchor": policy.requires_explicit_referential_anchor,
            "control_governance_referential_anchor_policy": (
                "after repeated confirmation cycles, referential requests should include an explicit commit anchor, an explicit node target, or an explicit non-latest selector before auto-resolution resumes"
            ),
            "control_governance_referential_anchor_examples": [
                "Rollback commit abc1234",
                "Undo the last change on node reviewer",
                "Revert the change before last",
            ],
            "control_governance_policy_tier": policy.tier,
            "control_governance_policy_reason": policy.reason,
            "control_governance_precheck_message": policy.precheck_message,
            "control_governance_preview_hint": policy.preview_hint,
            "control_governance_next_actions": list(policy.next_actions),
        }
    )
    return next_notes


def requires_explicit_referential_anchor(notes: Mapping[str, Any]) -> bool:
    return bool(notes.get("control_governance_requires_explicit_referential_anchor"))


def load_control_governance_policy(notes: Mapping[str, Any]) -> ControlGovernancePolicy:
    return ControlGovernancePolicy(
        tier=str(notes.get("control_governance_policy_tier", "standard")),
        interpretation_safety_mode=str(notes.get("control_governance_interpretation_safety_mode", "standard")),
        requires_explicit_referential_anchor=bool(notes.get("control_governance_requires_explicit_referential_anchor", False)),
        reason=str(notes.get("control_governance_policy_reason", "No repeated confirmation-governance escalation is currently active.")),
        precheck_message=str(notes.get("control_governance_precheck_message", "")),
        preview_hint=str(notes.get("control_governance_preview_hint", "")),
        next_actions=tuple(str(item) for item in notes.get("control_governance_next_actions", ()) if str(item).strip()),
    )


def _derive_control_governance_policy(*, repeated_reason_count: int, confirmation_loop_count: int) -> ControlGovernancePolicy:
    if confirmation_loop_count >= 3 or repeated_reason_count >= 3:
        return ControlGovernancePolicy(
            tier="strict",
            interpretation_safety_mode="explicit_referential_anchor_required",
            requires_explicit_referential_anchor=True,
            reason="Three or more closely related confirmation cycles were observed, so referential auto-resolution has moved into strict governance mode.",
            precheck_message="Repeated referential ambiguity has triggered strict governance mode. Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before approval can continue safely.",
            preview_hint="Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
            next_actions=("provide_explicit_anchor", "restate_request_with_stronger_selector"),
        )
    if confirmation_loop_count >= _REPEAT_CONFIRMATION_THRESHOLD:
        return ControlGovernancePolicy(
            tier="elevated",
            interpretation_safety_mode="explicit_referential_anchor_required",
            requires_explicit_referential_anchor=True,
            reason="Repeated confirmation-required cycles were detected, so referential auto-resolution is temporarily elevated into anchor-required mode.",
            precheck_message="Repeated referential ambiguity has triggered elevated governance mode. Add an explicit commit anchor, explicit node target, or explicit non-latest selector before relying on automatic rollback interpretation.",
            preview_hint="Elevated referential governance is active. The current request is previewable, but the next revision should include a stronger referential anchor.",
            next_actions=("provide_explicit_anchor",),
        )
    return ControlGovernancePolicy()


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
