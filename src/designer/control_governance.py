from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.designer.models.designer_session_state_card import RevisionAttemptSummary

_RECENT_ATTEMPT_LIMIT = 3
_REPEAT_CONFIRMATION_THRESHOLD = 2
_STRICT_REPEAT_THRESHOLD = 3

_TIER_RANK = {"standard": 0, "elevated": 1, "strict": 2}

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
        "control_governance_thresholds",
        "control_governance_transition_direction",
        "control_governance_transition_summary",
        "control_governance_previous_tier",
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


@dataclass(frozen=True)
class ControlGovernanceApplicability:
    policy: ControlGovernancePolicy
    is_referential_context: bool = False
    anchor_requirement_unsatisfied: bool = False
    anchor_requirement_satisfied: bool = False
    status_message: str = ""
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
    previous_tier = str(notes.get("control_governance_policy_tier", "standard"))
    transition_direction = _tier_transition_direction(previous_tier, policy.tier)
    transition_summary = _tier_transition_summary(previous_tier, policy.tier, transition_direction)

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
            "control_governance_thresholds": {
                "recent_attempt_limit": _RECENT_ATTEMPT_LIMIT,
                "elevated_confirmation_loop_threshold": _REPEAT_CONFIRMATION_THRESHOLD,
                "strict_repeat_threshold": _STRICT_REPEAT_THRESHOLD,
            },
            "control_governance_previous_tier": previous_tier,
            "control_governance_transition_direction": transition_direction,
            "control_governance_transition_summary": transition_summary,
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


def governance_applicability_for_request(
    *,
    ambiguity_flags: Sequence[Any],
    proposed_actions: Sequence[Any],
    notes: Mapping[str, Any],
) -> ControlGovernanceApplicability:
    policy = load_control_governance_policy(notes)
    repeat_cycle_flag = any(getattr(flag, "type", "") == "committed_summary_repeat_cycle_anchor_required" for flag in ambiguity_flags)
    referential_action_present = any(
        getattr(action, "parameters", {}).get("operation_mode") == "revert_committed_change"
        for action in proposed_actions
    )
    mixed_referential_context = any(
        str(getattr(flag, "type", "")).startswith("mixed_referential_")
        for flag in ambiguity_flags
    )
    is_referential_context = repeat_cycle_flag or referential_action_present or mixed_referential_context
    anchor_requirement_unsatisfied = repeat_cycle_flag and policy.requires_explicit_referential_anchor
    anchor_requirement_satisfied = referential_action_present and policy.requires_explicit_referential_anchor and not anchor_requirement_unsatisfied

    if not is_referential_context or policy.tier == "standard":
        return ControlGovernanceApplicability(policy=policy, is_referential_context=is_referential_context)
    if anchor_requirement_unsatisfied:
        return ControlGovernanceApplicability(
            policy=policy,
            is_referential_context=True,
            anchor_requirement_unsatisfied=True,
            status_message=policy.precheck_message or policy.reason,
            next_actions=policy.next_actions,
        )
    if anchor_requirement_satisfied:
        return ControlGovernanceApplicability(
            policy=policy,
            is_referential_context=True,
            anchor_requirement_satisfied=True,
            status_message=(
                f"{policy.tier.capitalize()} referential governance remains active, but the current request provides a strong enough anchor to continue safely."
            ),
            next_actions=("review_explicit_anchor", "continue_with_confirmation"),
        )
    return ControlGovernanceApplicability(
        policy=policy,
        is_referential_context=True,
        status_message=policy.reason,
        next_actions=policy.next_actions,
    )


def _derive_control_governance_policy(*, repeated_reason_count: int, confirmation_loop_count: int) -> ControlGovernancePolicy:
    if confirmation_loop_count >= _STRICT_REPEAT_THRESHOLD or repeated_reason_count >= _STRICT_REPEAT_THRESHOLD:
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


def _tier_transition_direction(previous_tier: str, current_tier: str) -> str:
    previous_rank = _TIER_RANK.get(previous_tier, 0)
    current_rank = _TIER_RANK.get(current_tier, 0)
    if current_rank > previous_rank:
        return "escalated"
    if current_rank < previous_rank:
        return "deescalated"
    return "unchanged"


def _tier_transition_summary(previous_tier: str, current_tier: str, direction: str) -> str:
    if direction == "escalated":
        return f"Control governance escalated from {previous_tier} to {current_tier} based on recent repeated confirmation patterns."
    if direction == "deescalated":
        return f"Control governance deescalated from {previous_tier} to {current_tier} after recent repeated confirmation pressure eased."
    return f"Control governance remains in {current_tier} mode."
