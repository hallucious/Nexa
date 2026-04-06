from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from dataclasses import dataclass
from typing import Any

from src.designer.models.designer_session_state_card import RevisionAttemptSummary

_RECENT_ATTEMPT_LIMIT = 3
_REPEAT_CONFIRMATION_THRESHOLD = 2
_STRICT_REPEAT_THRESHOLD = 3
_SAFE_CYCLE_DECAY_THRESHOLD = 2
_RECENT_ANCHOR_RESOLUTION_RETENTION_CYCLES = 1
_RECENT_REVISION_REDIRECT_ARCHIVE_RETENTION_CYCLES = 2
_RECENT_APPROVAL_REVISION_HISTORY_RETENTION_CYCLES = 2

_ELEVATED_PRESSURE_SCORE = 2
_STRICT_PRESSURE_SCORE = 4
_PRESSURE_SCORE_MAX = 5

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
        "control_governance_transition_rule",
        "control_governance_previous_tier",
        "control_governance_resolution_state",
        "control_governance_resolution_message",
        "control_governance_safe_cycle_decay_count",
        "control_governance_safe_cycle_decay_threshold",
        "control_governance_decay_summary",
        "control_governance_decay_path",
        "control_governance_ambiguity_pressure_score",
        "control_governance_previous_ambiguity_pressure_score",
        "control_governance_ambiguity_pressure_band",
        "control_governance_pressure_transition",
        "control_governance_pressure_summary",
    }
)

_ANCHORED_RESOLUTION_REASON_CODES = frozenset(
    {
        "DESIGNER-GOVERNANCE-ELEVATED-ANCHORED-READY",
        "DESIGNER-GOVERNANCE-STRICT-ANCHORED-READY",
        "DESIGNER-GOVERNANCE-ELEVATED-ANCHORED-CONFIRMATION",
        "DESIGNER-GOVERNANCE-STRICT-ANCHORED-CONFIRMATION",
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
class ControlGovernancePressure:
    score: int = 0
    previous_score: int = 0
    band: str = "standard"
    transition: str = "baseline"
    summary: str = ""


@dataclass(frozen=True)
class PendingAnchorCarryoverApplicability:
    status: str = "none"
    snapshot: dict[str, Any] | None = None
    explanation: str = ""
    next_actions: tuple[str, ...] = ()

    @property
    def is_unsatisfied(self) -> bool:
        return self.status == "unsatisfied"

    @property
    def is_anchored(self) -> bool:
        return self.status == "anchored_satisfied"

    @property
    def is_hidden_nonreferential(self) -> bool:
        return self.status == "hidden_nonreferential"


@dataclass(frozen=True)
class RecentAnchorResolutionApplicability:
    status: str = "none"
    snapshot: dict[str, Any] | None = None
    explanation: str = ""

    @property
    def is_visible_referential(self) -> bool:
        return self.status == "visible_referential"

    @property
    def is_hidden_nonreferential(self) -> bool:
        return self.status == "hidden_nonreferential"

    @property
    def is_expired(self) -> bool:
        return self.status == "expired_recent_followup"


@dataclass(frozen=True)
class RecentRevisionHistoryApplicability:
    status: str = "none"
    snapshot: dict[str, Any] | None = None
    explanation: str = ""

    @property
    def is_visible_mutation(self) -> bool:
        return self.status == "visible_mutation"

    @property
    def is_hidden_read_only(self) -> bool:
        return self.status == "hidden_read_only"

    @property
    def is_redirect_scope(self) -> bool:
        return self.status == "redirect_scope"

    @property
    def is_expired(self) -> bool:
        return self.status == "expired_recent_followup"


@dataclass(frozen=True)
class RecentRevisionRedirectArchiveApplicability:
    status: str = "none"
    snapshot: dict[str, Any] | None = None
    explanation: str = ""

    @property
    def is_visible_mutation(self) -> bool:
        return self.status == "visible_mutation"

    @property
    def is_reopen_mutation(self) -> bool:
        return self.status == "reopen_mutation"

    @property
    def is_hidden_read_only(self) -> bool:
        return self.status == "hidden_read_only"

    @property
    def is_expired(self) -> bool:
        return self.status == "expired_recent_followup"


def governance_pending_anchor_is_fully_satisfied(
    applicability: PendingAnchorCarryoverApplicability,
    *,
    governance_issue_codes: Sequence[str] = (),
) -> bool:
    if not applicability.is_anchored:
        return False
    return not any(
        is_governance_confirmation_issue_code(code) and not str(code).endswith("_ANCHORED")
        for code in governance_issue_codes
    )


def governance_pending_anchor_resolution_summary(
    applicability: PendingAnchorCarryoverApplicability,
) -> str:
    summary = applicability.explanation.strip()
    if applicability.next_actions:
        pretty = ", then ".join(str(item).replace("_", " ") for item in applicability.next_actions)
        suffix = f"Next safe step: {pretty}."
        return _join_governance_parts(summary, suffix)
    return summary


@dataclass(frozen=True)
class ControlGovernanceApplicability:
    policy: ControlGovernancePolicy
    is_referential_context: bool = False
    anchor_requirement_unsatisfied: bool = False
    anchor_requirement_satisfied: bool = False
    status_message: str = ""
    next_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ControlGovernanceDecision:
    applicability: ControlGovernanceApplicability
    pressure: ControlGovernancePressure = ControlGovernancePressure()
    applicability_status: str = "not_applicable"
    surface_mode: str = "hidden"
    explanation: str = ""
    recommended_next_actions: tuple[str, ...] = ()
    approval_guidance: str = ""
    revision_guidance: str = ""

    @property
    def policy(self) -> ControlGovernancePolicy:
        return self.applicability.policy


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
    previous_policy = load_control_governance_policy(notes)
    previous_safe_cycle_decay_count = int(notes.get("control_governance_safe_cycle_decay_count", 0) or 0)
    base_policy = _derive_control_governance_policy(
        repeated_reason_count=repeated_reason_count,
        confirmation_loop_count=confirmation_loop_count,
    )
    (
        policy,
        transition_direction,
        transition_summary,
        transition_rule,
        resolution_state,
        resolution_message,
        safe_cycle_decay_count,
        decay_summary,
        decay_path,
    ) = _apply_policy_transition(
        previous_policy=previous_policy,
        base_policy=base_policy,
        latest_attempt=latest,
        previous_safe_cycle_decay_count=previous_safe_cycle_decay_count,
    )
    previous_tier = previous_policy.tier
    previous_pressure_score = int(
        notes.get("control_governance_ambiguity_pressure_score", _pressure_score_floor_for_tier(previous_tier)) or 0
    )
    (
        pressure_score,
        pressure_band,
        pressure_transition,
        pressure_summary,
    ) = _apply_pressure_transition(
        previous_score=previous_pressure_score,
        previous_policy=previous_policy,
        current_policy=policy,
        transition_rule=transition_rule,
        resolution_state=resolution_state,
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
            "control_governance_thresholds": {
                "recent_attempt_limit": _RECENT_ATTEMPT_LIMIT,
                "elevated_confirmation_loop_threshold": _REPEAT_CONFIRMATION_THRESHOLD,
                "strict_repeat_threshold": _STRICT_REPEAT_THRESHOLD,
                "elevated_pressure_score": _ELEVATED_PRESSURE_SCORE,
                "strict_pressure_score": _STRICT_PRESSURE_SCORE,
                "pressure_score_max": _PRESSURE_SCORE_MAX,
            },
            "control_governance_previous_tier": previous_tier,
            "control_governance_transition_direction": transition_direction,
            "control_governance_transition_summary": transition_summary,
            "control_governance_transition_rule": transition_rule,
            "control_governance_resolution_state": resolution_state,
            "control_governance_resolution_message": resolution_message,
            "control_governance_safe_cycle_decay_count": safe_cycle_decay_count,
            "control_governance_safe_cycle_decay_threshold": _SAFE_CYCLE_DECAY_THRESHOLD,
            "control_governance_decay_summary": decay_summary,
            "control_governance_decay_path": decay_path,
            "control_governance_previous_ambiguity_pressure_score": previous_pressure_score,
            "control_governance_ambiguity_pressure_score": pressure_score,
            "control_governance_ambiguity_pressure_band": pressure_band,
            "control_governance_pressure_transition": pressure_transition,
            "control_governance_pressure_summary": pressure_summary,
        }
    )
    return next_notes


def requires_explicit_referential_anchor(notes: Mapping[str, Any]) -> bool:
    return bool(notes.get("control_governance_requires_explicit_referential_anchor"))


def load_control_governance_policy(notes: Mapping[str, Any]) -> ControlGovernancePolicy:
    tier = str(notes.get("control_governance_policy_tier", "standard"))
    defaults = _policy_defaults_for_tier(tier)
    raw_next_actions = tuple(str(item) for item in notes.get("control_governance_next_actions", ()) if str(item).strip())
    return ControlGovernancePolicy(
        tier=tier,
        interpretation_safety_mode=str(notes.get("control_governance_interpretation_safety_mode", defaults.interpretation_safety_mode)),
        requires_explicit_referential_anchor=bool(notes.get("control_governance_requires_explicit_referential_anchor", defaults.requires_explicit_referential_anchor)),
        reason=str(notes.get("control_governance_policy_reason", defaults.reason)),
        precheck_message=str(notes.get("control_governance_precheck_message", defaults.precheck_message)),
        preview_hint=str(notes.get("control_governance_preview_hint", defaults.preview_hint)),
        next_actions=raw_next_actions or defaults.next_actions,
    )


def load_control_governance_pressure(notes: Mapping[str, Any]) -> ControlGovernancePressure:
    policy = load_control_governance_policy(notes)
    previous_score = int(notes.get("control_governance_previous_ambiguity_pressure_score", _pressure_score_floor_for_tier(policy.tier)) or 0)
    score = int(notes.get("control_governance_ambiguity_pressure_score", _pressure_score_floor_for_tier(policy.tier)) or 0)
    band = str(notes.get("control_governance_ambiguity_pressure_band", _pressure_band_for_score(score)))
    transition = str(notes.get("control_governance_pressure_transition", "baseline"))
    summary = str(notes.get("control_governance_pressure_summary", _default_pressure_summary(score=score, band=band, transition=transition)))
    return ControlGovernancePressure(
        score=score,
        previous_score=previous_score,
        band=band,
        transition=transition,
        summary=summary,
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


def governance_decision_for_request(
    *,
    ambiguity_flags: Sequence[Any],
    proposed_actions: Sequence[Any],
    notes: Mapping[str, Any],
) -> ControlGovernanceDecision:
    applicability = governance_applicability_for_request(
        ambiguity_flags=ambiguity_flags,
        proposed_actions=proposed_actions,
        notes=notes,
    )
    policy = applicability.policy
    pressure = load_control_governance_pressure(notes)
    if policy.tier == "standard" or not applicability.is_referential_context:
        return ControlGovernanceDecision(
            applicability=applicability,
            pressure=pressure,
            applicability_status="not_applicable" if not applicability.is_referential_context else "standard",
            surface_mode="hidden",
            explanation=applicability.status_message or policy.reason,
        )
    if applicability.anchor_requirement_unsatisfied:
        base_explanation = applicability.status_message or policy.precheck_message or policy.reason
        explanation = _join_governance_parts(base_explanation, _pressure_surface_summary(pressure, surface_mode="confirmation_required"))
        revision_guidance = _join_governance_parts(
            "Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before the next revision attempt.",
            _pressure_surface_summary(pressure, surface_mode="revision_required"),
        )
        return ControlGovernanceDecision(
            applicability=applicability,
            pressure=pressure,
            applicability_status="unsatisfied",
            surface_mode="confirmation_required",
            explanation=explanation,
            recommended_next_actions=applicability.next_actions or policy.next_actions,
            approval_guidance=explanation,
            revision_guidance=revision_guidance,
        )
    if applicability.anchor_requirement_satisfied:
        base_explanation = applicability.status_message or policy.reason
        explanation = _join_governance_parts(base_explanation, _pressure_surface_summary(pressure, surface_mode="warning"))
        return ControlGovernanceDecision(
            applicability=applicability,
            pressure=pressure,
            applicability_status="satisfied",
            surface_mode="warning",
            explanation=explanation,
            recommended_next_actions=applicability.next_actions or ("review_explicit_anchor", "continue_with_confirmation"),
            approval_guidance=_join_governance_parts(
                "The current request is anchored strongly enough to continue under the elevated governance tier.",
                _pressure_surface_summary(pressure, surface_mode="warning"),
            ),
            revision_guidance=_join_governance_parts(
                "Keep future referential revisions explicit while governance remains elevated.",
                _pressure_surface_summary(pressure, surface_mode="revision_warning"),
            ),
        )
    base_explanation = applicability.status_message or policy.reason
    explanation = _join_governance_parts(base_explanation, _pressure_surface_summary(pressure, surface_mode="info"))
    return ControlGovernanceDecision(
        applicability=applicability,
        pressure=pressure,
        applicability_status="informational",
        surface_mode="info",
        explanation=explanation,
        recommended_next_actions=applicability.next_actions or policy.next_actions,
        approval_guidance=explanation,
        revision_guidance=_join_governance_parts(
            "If the next revision uses referential language, keep the selector explicit while governance remains elevated.",
            _pressure_surface_summary(pressure, surface_mode="revision_info"),
        ),
    )

def is_governance_confirmation_issue_code(issue_code: str) -> bool:
    return issue_code.startswith("REFERENTIAL_GOVERNANCE_")


def is_governance_decision_id(decision_id: str) -> bool:
    return decision_id.startswith("referential_governance_")


def governance_pending_anchor_applicability_for_request(
    notes: Mapping[str, Any],
    request_text: str,
    *,
    available_node_refs: Sequence[str] = (),
    commit_history: Sequence[Mapping[str, Any]] = (),
) -> PendingAnchorCarryoverApplicability:
    snapshot = governance_pending_anchor_snapshot_from_notes(notes)
    if not snapshot:
        return PendingAnchorCarryoverApplicability(status="none", snapshot={})
    if not _uses_referential_request_language(request_text):
        return PendingAnchorCarryoverApplicability(
            status="hidden_nonreferential",
            snapshot=snapshot,
            explanation="Pending governance carryover remains stored, but the current request is not in the risky referential category.",
        )
    if _request_has_explicit_anchor(
        request_text,
        available_node_refs=available_node_refs,
        commit_history=commit_history,
    ):
        pressure_summary = str(snapshot.get("pressure_summary", "")).strip()
        explanation = "Pending governance carryover remains visible, but the current request already provides a stronger referential anchor."
        if pressure_summary:
            explanation = f"{explanation} {pressure_summary}"
        return PendingAnchorCarryoverApplicability(
            status="anchored_satisfied",
            snapshot=snapshot,
            explanation=explanation,
            next_actions=tuple(str(item) for item in snapshot.get("next_actions", ()) if str(item).strip()),
        )
    return PendingAnchorCarryoverApplicability(
        status="unsatisfied",
        snapshot=snapshot,
        explanation=str(snapshot.get("message", "")).strip(),
        next_actions=tuple(str(item) for item in snapshot.get("next_actions", ()) if str(item).strip()),
    )


def _uses_referential_request_language(request_text: str) -> bool:
    text = request_text.casefold()
    patterns = (
        r"\bprevious change\b",
        r"\blast change\b",
        r"\bprevious commit\b",
        r"\blast commit\b",
        r"\bsame change\b",
        r"\bsame edit\b",
        r"\bthat change\b",
        r"\bthat edit\b",
        r"\brevert\b",
        r"\bundo\b",
        r"\brollback\b",
        r"\broll back\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _uses_second_latest_reference_language(request_text: str) -> bool:
    text = request_text.casefold()
    patterns = (
        r"\b(second last|second-latest|before last|prior to last|the one before that) (change|commit|edit)\b",
        r"\b(change|commit|edit) before last\b",
        r"\bcommit before last\b",
        r"\bchange before last\b",
        r"\bthe one before that\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _extract_node_refs_for_governance(request_text: str) -> tuple[str, ...]:
    prioritized_patterns = (
        r"\bin\s+node\s+([A-Za-z0-9_\-\.]+)",
        r"\bon\s+node\s+([A-Za-z0-9_\-\.]+)",
        r"\bfor\s+node\s+([A-Za-z0-9_\-\.]+)",
        r"\bat\s+node\s+([A-Za-z0-9_\-\.]+)",
        r"\bnode\.([A-Za-z0-9_\-\.]+)",
        r"\bnode\s+([A-Za-z0-9_\-\.]+)",
    )
    stopwords = {"before", "after", "between", "final", "a", "an", "the"}
    ordered_refs: list[str] = []
    seen: set[str] = set()
    for pattern in prioritized_patterns:
        for match in re.finditer(pattern, request_text, flags=re.IGNORECASE):
            ref = match.group(1).rstrip(".,;:")
            if ref.casefold() in stopwords:
                continue
            if ref not in seen:
                ordered_refs.append(ref)
                seen.add(ref)
    return tuple(ordered_refs)


def _resolve_node_refs_for_governance(
    node_refs: Sequence[str],
    *,
    available_node_refs: Sequence[str],
) -> tuple[str, ...]:
    if not node_refs:
        return ()
    candidates = tuple(str(item) for item in available_node_refs if str(item).strip())
    if not candidates:
        return tuple(str(item) for item in node_refs if str(item).strip())
    resolved: list[str] = []
    for ref in node_refs:
        if ref in candidates:
            resolved.append(ref)
            continue
        suffix_matches = [item for item in candidates if item.endswith(f".{ref}")]
        if len(suffix_matches) == 1:
            resolved.append(suffix_matches[0])
        else:
            resolved.append(str(ref))
    return tuple(dict.fromkeys(item for item in resolved if item))


def _match_explicit_commit_reference_for_governance(
    request_text: str,
    *,
    commit_history: Sequence[Mapping[str, Any]],
) -> bool:
    text = request_text.casefold()
    commit_tokens = set(re.findall(r"\b[a-f0-9]{7,40}\b", text))
    if not commit_tokens:
        return False
    history = [dict(item) for item in commit_history if isinstance(item, Mapping)]
    if not history:
        return True
    for item in history:
        commit_id = str(item.get("commit_id", "")).casefold()
        if any(commit_id.startswith(token) for token in commit_tokens):
            return True
    return False


def _request_has_explicit_anchor(
    request_text: str,
    *,
    available_node_refs: Sequence[str] = (),
    commit_history: Sequence[Mapping[str, Any]] = (),
) -> bool:
    if _match_explicit_commit_reference_for_governance(request_text, commit_history=commit_history):
        return True
    if _uses_second_latest_reference_language(request_text):
        return True
    explicit_node_refs = _resolve_node_refs_for_governance(
        _extract_node_refs_for_governance(request_text),
        available_node_refs=available_node_refs,
    )
    return bool(explicit_node_refs)


def _request_explicitly_redirects_recent_revision_scope(
    request_text: str,
    *,
    latest_selected_interpretation: str,
    available_node_refs: Sequence[str] = (),
) -> bool:
    if not request_text.strip() or not latest_selected_interpretation.strip():
        return False
    request_refs = set(
        _resolve_node_refs_for_governance(
            _extract_node_refs_for_governance(request_text),
            available_node_refs=available_node_refs,
        )
    )
    latest_refs = set(
        _resolve_node_refs_for_governance(
            _extract_node_refs_for_governance(latest_selected_interpretation),
            available_node_refs=available_node_refs,
        )
    )
    if request_refs and latest_refs and request_refs.isdisjoint(latest_refs):
        return True
    text = request_text.casefold()
    redirect_patterns = (
        r"instead",
        r"rather than",
        r"switch to",
        r"focus on",
        r"redirect scope",
        r"different node",
    )
    return bool(request_refs) and any(re.search(pattern, text) for pattern in redirect_patterns)


def governance_revision_guidance_from_notes(notes: Mapping[str, Any]) -> str:
    snapshot = governance_revision_snapshot_from_notes(notes)
    return snapshot.get("message", "") if snapshot else ""


def governance_revision_snapshot_from_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    policy = load_control_governance_policy(notes)
    pressure = load_control_governance_pressure(notes)
    if not policy.requires_explicit_referential_anchor:
        return {}
    if policy.tier == "strict":
        mode = "required"
        next_actions = ("provide_explicit_anchor", "restate_request_with_stronger_selector")
        message = _join_governance_parts(
            "Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before the next revision attempt.",
            _pressure_surface_summary(pressure, surface_mode="revision_required"),
        )
    elif policy.tier == "elevated":
        mode = "preferred"
        next_actions = ("provide_explicit_anchor",)
        message = _join_governance_parts(
            "Prefer an explicit commit anchor, explicit node target, or explicit non-latest selector in the next revision attempt.",
            _pressure_surface_summary(pressure, surface_mode="revision_warning"),
        )
    else:
        return {}
    return {
        "mode": mode,
        "message": message,
        "pressure_summary": pressure.summary,
        "pressure_score": pressure.score,
        "pressure_band": pressure.band,
        "pressure_transition": pressure.transition,
        "next_actions": list(next_actions),
    }


def governance_pending_anchor_snapshot_from_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    if not bool(notes.get("control_governance_pending_anchor_requirement")):
        return {}

    mode = str(notes.get("control_governance_pending_anchor_requirement_mode", "required"))
    pressure_score = int(notes.get("control_governance_last_revision_pressure_score", 0) or 0)
    pressure_band = str(notes.get("control_governance_last_revision_pressure_band", _pressure_band_for_score(pressure_score)))
    pressure_transition = str(notes.get("control_governance_pressure_transition", "baseline"))
    pressure_summary = str(
        notes.get(
            "control_governance_last_revision_pressure_summary",
            _default_pressure_summary(score=pressure_score, band=pressure_band, transition=pressure_transition),
        )
    )
    next_actions = [
        str(item)
        for item in notes.get("control_governance_last_revision_next_actions", ())
        if str(item).strip()
    ]
    guidance = str(notes.get("control_governance_last_revision_guidance", "")).strip()

    if not guidance or not next_actions:
        derived = governance_revision_snapshot_from_notes(notes)
        if derived:
            mode = str(notes.get("control_governance_pending_anchor_requirement_mode", derived.get("mode", mode)))
            pressure_summary = pressure_summary or str(derived.get("pressure_summary", "")).strip()
            pressure_score = int(notes.get("control_governance_last_revision_pressure_score", derived.get("pressure_score", pressure_score)) or 0)
            pressure_band = str(notes.get("control_governance_last_revision_pressure_band", derived.get("pressure_band", pressure_band)))
            guidance = guidance or str(derived.get("message", "")).strip()
            if not next_actions:
                next_actions = [str(item) for item in derived.get("next_actions", ()) if str(item).strip()]

    return {
        "mode": mode,
        "message": guidance,
        "pressure_summary": pressure_summary,
        "pressure_score": pressure_score,
        "pressure_band": pressure_band,
        "next_actions": next_actions,
    }


def governance_pending_anchor_summary_from_notes(notes: Mapping[str, Any]) -> str:
    snapshot = governance_pending_anchor_snapshot_from_notes(notes)
    if not snapshot:
        return ""
    parts = [str(snapshot.get("message", "")).strip(), str(snapshot.get("pressure_summary", "")).strip()]
    if snapshot.get("next_actions"):
        pretty = ", then ".join(str(item).replace("_", " ") for item in snapshot["next_actions"])
        parts.append(f"Next safe step: {pretty}.")
    return _join_governance_parts(*parts)


def governance_recent_anchor_resolution_snapshot_from_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    status = str(notes.get("control_governance_last_pending_anchor_resolution_status", "")).strip()
    if not status:
        return {}
    return {
        "status": status,
        "summary": str(notes.get("control_governance_last_pending_anchor_resolution_summary", "")).strip(),
        "request_text": str(notes.get("control_governance_last_pending_anchor_resolution_request_text", "")).strip(),
        "age": int(notes.get("control_governance_last_pending_anchor_resolution_age", 0) or 0),
    }


def clear_recent_anchor_resolution_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    next_notes = dict(notes)
    next_notes.pop("control_governance_last_pending_anchor_resolution_status", None)
    next_notes.pop("control_governance_last_pending_anchor_resolution_summary", None)
    next_notes.pop("control_governance_last_pending_anchor_resolution_request_text", None)
    next_notes.pop("control_governance_last_pending_anchor_resolution_age", None)
    return next_notes


def advance_recent_anchor_resolution_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = governance_recent_anchor_resolution_snapshot_from_notes(notes)
    if not snapshot:
        return dict(notes)
    next_age = int(snapshot.get("age", 0) or 0) + 1
    if next_age >= _RECENT_ANCHOR_RESOLUTION_RETENTION_CYCLES:
        return clear_recent_anchor_resolution_notes(notes)
    next_notes = dict(notes)
    next_notes["control_governance_last_pending_anchor_resolution_age"] = next_age
    return next_notes


def governance_recent_anchor_resolution_applicability_for_request(
    notes: Mapping[str, Any],
    request_text: str,
    *,
    available_node_refs: Sequence[str] = (),
    commit_history: Sequence[Mapping[str, Any]] = (),
) -> RecentAnchorResolutionApplicability:
    snapshot = governance_recent_anchor_resolution_snapshot_from_notes(notes)
    if not snapshot:
        return RecentAnchorResolutionApplicability(status="none", snapshot={})
    if int(snapshot.get("age", 0) or 0) >= _RECENT_ANCHOR_RESOLUTION_RETENTION_CYCLES:
        return RecentAnchorResolutionApplicability(
            status="expired_recent_followup",
            snapshot=snapshot,
            explanation="A previously cleared governance carryover is now outside the recent-resolution retention window.",
        )
    if bool(notes.get("control_governance_pending_anchor_requirement")):
        return RecentAnchorResolutionApplicability(status="superseded_by_pending", snapshot=snapshot)
    if not _uses_referential_request_language(request_text):
        return RecentAnchorResolutionApplicability(
            status="hidden_nonreferential",
            snapshot=snapshot,
            explanation="A previous governance anchor requirement was resolved recently, but the current request is not in the referential category.",
        )
    base_summary = str(snapshot.get("summary", "")).strip()
    resolution = "A previous governance anchor requirement was recently cleared by an explicit anchored retry."
    if _request_has_explicit_anchor(
        request_text,
        available_node_refs=available_node_refs,
        commit_history=commit_history,
    ):
        explanation = _join_governance_parts(resolution, base_summary)
    else:
        explanation = _join_governance_parts(
            resolution,
            "The current referential request is not currently blocked by the old pending carryover, but future ambiguity may still re-escalate governance if selectors become loose again.",
            base_summary,
        )
    return RecentAnchorResolutionApplicability(
        status="visible_referential",
        snapshot=snapshot,
        explanation=explanation,
    )


def governance_recent_revision_redirect_archive_snapshot_from_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    status = str(notes.get("approval_revision_redirect_archived_status", "")).strip()
    if not status:
        return {}
    raw_history = notes.get("approval_revision_redirect_archived_history", ())
    history = [dict(item) for item in raw_history if isinstance(item, Mapping)] if isinstance(raw_history, (list, tuple)) else []
    return {
        "status": status,
        "summary": str(notes.get("approval_revision_redirect_archived_summary", "")).strip(),
        "history": history,
        "count": int(notes.get("approval_revision_redirect_archived_count", len(history)) or 0),
        "age": int(notes.get("approval_revision_redirect_archived_age", 0) or 0),
    }


def clear_recent_revision_redirect_archive_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    next_notes = dict(notes)
    for key in (
        "approval_revision_redirect_archived_status",
        "approval_revision_redirect_archived_summary",
        "approval_revision_redirect_archived_applied",
        "approval_revision_redirect_archived_history",
        "approval_revision_redirect_archived_count",
        "approval_revision_redirect_archived_age",
    ):
        next_notes.pop(key, None)
    return next_notes


def advance_recent_revision_redirect_archive_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = governance_recent_revision_redirect_archive_snapshot_from_notes(notes)
    if not snapshot:
        return dict(notes)
    next_age = int(snapshot.get("age", 0) or 0) + 1
    if next_age >= _RECENT_REVISION_REDIRECT_ARCHIVE_RETENTION_CYCLES:
        return clear_recent_revision_redirect_archive_notes(notes)
    next_notes = dict(notes)
    next_notes["approval_revision_redirect_archived_age"] = next_age
    return next_notes


def governance_recent_revision_redirect_archive_applicability_for_request(
    notes: Mapping[str, Any],
    request_text: str,
    *,
    mutation_oriented: bool,
    available_node_refs: Sequence[str] = (),
) -> RecentRevisionRedirectArchiveApplicability:
    snapshot = governance_recent_revision_redirect_archive_snapshot_from_notes(notes)
    if not snapshot:
        return RecentRevisionRedirectArchiveApplicability(status="none", snapshot={})
    if int(snapshot.get("age", 0) or 0) >= _RECENT_REVISION_REDIRECT_ARCHIVE_RETENTION_CYCLES:
        return RecentRevisionRedirectArchiveApplicability(
            status="expired_recent_followup",
            snapshot=snapshot,
            explanation="A previous revision-thread redirect archive is now outside the short-lived background-retention window.",
        )
    if not mutation_oriented:
        return RecentRevisionRedirectArchiveApplicability(
            status="hidden_read_only",
            snapshot=snapshot,
            explanation="A previous revision-thread redirect remains hidden background context for read-only follow-up requests.",
        )
    latest_selected_interpretation = ""
    history = snapshot.get("history", [])
    if isinstance(history, list) and history:
        latest_selected_interpretation = str(history[-1].get("selected_interpretation", "")).strip()
    request_refs = set(
        _resolve_node_refs_for_governance(
            _extract_node_refs_for_governance(request_text),
            available_node_refs=available_node_refs,
        )
    )
    latest_refs = set(
        _resolve_node_refs_for_governance(
            _extract_node_refs_for_governance(latest_selected_interpretation),
            available_node_refs=available_node_refs,
        )
    )
    if request_refs and latest_refs and not request_refs.isdisjoint(latest_refs):
        return RecentRevisionRedirectArchiveApplicability(
            status="reopen_mutation",
            snapshot=snapshot,
            explanation=(
                "The current mutation request explicitly returns to the older redirected scope, so the archived revision thread should be restored as active continuity again."
            ),
        )
    return RecentRevisionRedirectArchiveApplicability(
        status="visible_mutation",
        snapshot=snapshot,
        explanation=(
            "A previous revision thread was explicitly redirected away from its older scope and now remains only as short-lived background history; do not revive that older thread unless the user explicitly reopens it."
        ),
    )


def governance_recent_revision_history_snapshot_from_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    raw_history = notes.get("approval_revision_recent_history", ())
    history = [dict(item) for item in raw_history if isinstance(item, Mapping)] if isinstance(raw_history, (list, tuple)) else []
    if len(history) < 2:
        return {}
    latest = history[-1]
    origin_status = str(notes.get("approval_revision_recent_history_origin_status", "")).strip()
    origin_summary = str(notes.get("approval_revision_recent_history_origin_summary", "")).strip()
    return {
        "count": len(history),
        "summary": str(notes.get("approval_revision_recent_history_summary", "")).strip(),
        "history": history,
        "latest_selected_interpretation": str(latest.get("selected_interpretation", "")).strip(),
        "age": int(notes.get("approval_revision_recent_history_age", 0) or 0),
        "origin_status": origin_status,
        "origin_summary": origin_summary,
        "reopened_from_redirect_archive": origin_status == "reopened_from_redirect_archive",
    }


def clear_recent_revision_history_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    next_notes = dict(notes)
    for key in (
        "approval_revision_recent_history",
        "approval_revision_recent_history_count",
        "approval_revision_recent_history_summary",
        "approval_revision_recent_history_age",
        "approval_revision_recent_history_origin_status",
        "approval_revision_recent_history_origin_summary",
        "approval_revision_recent_history_origin_applied",
        "approval_revision_recent_history_reopened_status",
        "approval_revision_recent_history_reopened_summary",
        "approval_revision_recent_history_reopened_applied",
    ):
        next_notes.pop(key, None)
    return next_notes


def advance_recent_revision_history_notes(notes: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = governance_recent_revision_history_snapshot_from_notes(notes)
    if not snapshot:
        return dict(notes)
    next_age = int(snapshot.get("age", 0) or 0) + 1
    if next_age >= _RECENT_APPROVAL_REVISION_HISTORY_RETENTION_CYCLES:
        return clear_recent_revision_history_notes(notes)
    next_notes = dict(notes)
    next_notes["approval_revision_recent_history_age"] = next_age
    return next_notes


def governance_recent_revision_history_applicability_for_request(
    notes: Mapping[str, Any],
    request_text: str,
    *,
    mutation_oriented: bool,
    available_node_refs: Sequence[str] = (),
) -> RecentRevisionHistoryApplicability:
    snapshot = governance_recent_revision_history_snapshot_from_notes(notes)
    if not snapshot:
        return RecentRevisionHistoryApplicability(status="none", snapshot={})
    if int(snapshot.get("age", 0) or 0) >= _RECENT_APPROVAL_REVISION_HISTORY_RETENTION_CYCLES:
        return RecentRevisionHistoryApplicability(
            status="expired_recent_followup",
            snapshot=snapshot,
            explanation="A previous multi-step approval/revision continuity thread is now outside the short-lived active-retention window.",
        )
    selected = str(snapshot.get("latest_selected_interpretation", "")).strip()
    if not mutation_oriented:
        return RecentRevisionHistoryApplicability(
            status="hidden_read_only",
            snapshot=snapshot,
            explanation="The current request is read-only, so recent approval/revision continuity remains hidden background context.",
        )
    if _request_explicitly_redirects_recent_revision_scope(
        request_text,
        latest_selected_interpretation=selected,
        available_node_refs=available_node_refs,
    ):
        return RecentRevisionHistoryApplicability(
            status="redirect_scope",
            snapshot=snapshot,
            explanation=(
                "The current mutation request appears to intentionally redirect scope away from the latest clarified interpretation, so recent approval/revision continuity should remain background history instead of constraining the next mutation."
            ),
        )
    return RecentRevisionHistoryApplicability(
        status="visible_mutation",
        snapshot=snapshot,
        explanation=(
            "The current mutation request continues a recent multi-step approval/revision thread and should preserve the latest clarified interpretation unless the user explicitly redirects scope."
        ),
    )


def governance_anchored_progress_reason_code_from_issue_codes(
    issue_codes: Sequence[str],
    *,
    outcome: str,
) -> str | None:
    suffix = "READY" if outcome == "ready_for_approval" else "CONFIRMATION"
    for code in issue_codes:
        if code == "REFERENTIAL_GOVERNANCE_STRICT_ANCHORED":
            return f"DESIGNER-GOVERNANCE-STRICT-ANCHORED-{suffix}"
        if code == "REFERENTIAL_GOVERNANCE_ELEVATED_ANCHORED":
            return f"DESIGNER-GOVERNANCE-ELEVATED-ANCHORED-{suffix}"
    return None



def _join_governance_parts(*parts: str) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return " ".join(cleaned)


def _default_pressure_summary(*, score: int, band: str, transition: str) -> str:
    if score <= 0 or band == "standard":
        return "Ambiguity pressure is clear."
    if transition == "escalating_or_sustained_repeat_pressure":
        return f"Ambiguity pressure is high and still building ({score}/{_PRESSURE_SCORE_MAX}, {band} band)."
    if transition in {"anchored_relief_step", "safe_cycle_relief_step", "safe_cycle_relief_progress"}:
        return f"Ambiguity pressure is easing but still active ({score}/{_PRESSURE_SCORE_MAX}, {band} band)."
    if transition in {"anchored_relief_cleared", "safe_cycle_relief_cleared"}:
        return "Ambiguity pressure has been cleared."
    if transition == "held_until_resolution":
        return f"Ambiguity pressure remains held ({score}/{_PRESSURE_SCORE_MAX}, {band} band)."
    return f"Ambiguity pressure is {score}/{_PRESSURE_SCORE_MAX} ({band} band)."


def _pressure_surface_summary(pressure: ControlGovernancePressure, *, surface_mode: str) -> str:
    if pressure.score <= 0 or pressure.band == "standard":
        return ""
    if surface_mode == "confirmation_required":
        if pressure.transition == "escalating_or_sustained_repeat_pressure":
            return f"Current ambiguity pressure remains high ({pressure.score}/{_PRESSURE_SCORE_MAX}, {pressure.band} band), so stronger anchoring is still required."
        if pressure.transition in {"safe_cycle_relief_progress", "safe_cycle_relief_step", "anchored_relief_step"}:
            return f"Ambiguity pressure is easing but still active ({pressure.score}/{_PRESSURE_SCORE_MAX}, {pressure.band} band), so stronger anchoring is still required for now."
        return f"Current ambiguity pressure is {pressure.score}/{_PRESSURE_SCORE_MAX} ({pressure.band} band)."
    if surface_mode == "warning":
        return f"Ambiguity pressure remains {pressure.score}/{_PRESSURE_SCORE_MAX} ({pressure.band} band), so future referential edits should stay explicit even though the current request is anchored well enough."
    if surface_mode == "revision_required":
        return f"Ambiguity pressure remains {pressure.score}/{_PRESSURE_SCORE_MAX} ({pressure.band} band), so do not fall back to loose 'last change' style selectors in the next revision."
    if surface_mode == "revision_warning":
        return f"Ambiguity pressure is still elevated ({pressure.score}/{_PRESSURE_SCORE_MAX}, {pressure.band} band), so keep the next referential revision explicit as well."
    if surface_mode == "revision_info":
        return f"Ambiguity pressure is still visible ({pressure.score}/{_PRESSURE_SCORE_MAX}, {pressure.band} band)."
    return pressure.summary or _default_pressure_summary(score=pressure.score, band=pressure.band, transition=pressure.transition)

def _apply_policy_transition(
    *,
    previous_policy: ControlGovernancePolicy,
    base_policy: ControlGovernancePolicy,
    latest_attempt: RevisionAttemptSummary,
    previous_safe_cycle_decay_count: int,
) -> tuple[ControlGovernancePolicy, str, str, str, str, str, int, str, str]:
    if base_policy.tier != "standard":
        direction = _tier_transition_direction(previous_policy.tier, base_policy.tier)
        return (
            base_policy,
            direction,
            _tier_transition_summary(previous_tier=previous_policy.tier, current_tier=base_policy.tier, direction=direction),
            "repeat_confirmation_threshold",
            "active_repeat_pressure",
            "Recent repeated confirmation pressure still exceeds the escalation threshold.",
            0,
            "Active repeat pressure reset any safe-cycle decay progress.",
            "repeat_confirmation_pressure",
        )

    if previous_policy.requires_explicit_referential_anchor and previous_policy.tier in {"elevated", "strict"}:
        if latest_attempt.reason_code in _ANCHORED_RESOLUTION_REASON_CODES:
            if previous_policy.tier == "strict":
                policy = _anchored_cooldown_policy(previous_tier="strict")
                direction = _tier_transition_direction(previous_policy.tier, policy.tier)
                return (
                    policy,
                    direction,
                    "Control governance deescalated from strict to elevated after an anchored referential request resolved the current cycle, but one cooldown tier is retained for the next cycle.",
                    "anchored_resolution_cooldown",
                    "partial_relief",
                    "An explicit anchor resolved the latest strict-cycle request, so governance has relaxed by one tier but remains elevated during cooldown.",
                    0,
                    "Explicit anchored resolution immediately relaxed governance by one tier.",
                    "explicit_anchor_resolution",
                )
            direction = _tier_transition_direction(previous_policy.tier, "standard")
            return (
                ControlGovernancePolicy(),
                direction,
                "Control governance returned to standard after an anchored referential request resolved the elevated cycle.",
                "anchored_resolution_cleared",
                "cleared",
                "An explicit anchor resolved the elevated referential cycle, so the temporary anchor requirement has been cleared.",
                0,
                "Explicit anchored resolution cleared the remaining elevated governance tier.",
                "explicit_anchor_resolution",
            )

        if _is_safe_cycle_decay_candidate(latest_attempt):
            next_safe_cycle_decay_count = previous_safe_cycle_decay_count + 1
            if next_safe_cycle_decay_count >= _SAFE_CYCLE_DECAY_THRESHOLD:
                if previous_policy.tier == "strict":
                    policy = _safe_cycle_decay_policy(previous_tier="strict")
                    direction = _tier_transition_direction(previous_policy.tier, policy.tier)
                    return (
                        policy,
                        direction,
                        f"Control governance deescalated from strict to elevated after {next_safe_cycle_decay_count} consecutive safe non-referential cycles reduced recent ambiguity pressure.",
                        "safe_cycle_decay_threshold",
                        "safe_cycle_partial_relief",
                        "Sustained safe non-referential cycles reduced ambiguity pressure enough to relax strict governance by one tier.",
                        0,
                        f"{next_safe_cycle_decay_count} consecutive safe non-referential cycles reached the decay threshold and relaxed governance by one tier.",
                        "safe_nonreferential_cycles",
                    )
                direction = _tier_transition_direction(previous_policy.tier, "standard")
                return (
                    ControlGovernancePolicy(),
                    direction,
                    f"Control governance returned to standard after {next_safe_cycle_decay_count} consecutive safe non-referential cycles reduced the remaining ambiguity pressure.",
                    "safe_cycle_decay_threshold",
                    "safe_cycle_cleared",
                    "Sustained safe non-referential cycles reduced ambiguity pressure enough to clear the remaining elevated governance tier.",
                    0,
                    f"{next_safe_cycle_decay_count} consecutive safe non-referential cycles cleared the remaining elevated governance tier.",
                    "safe_nonreferential_cycles",
                )
            return (
                previous_policy,
                "held",
                f"Control governance remains in {previous_policy.tier} mode while safe-cycle decay progresses ({next_safe_cycle_decay_count}/{_SAFE_CYCLE_DECAY_THRESHOLD}).",
                "safe_cycle_decay_progress",
                "safe_cycle_decay_progress",
                "Recent safe non-referential work is reducing ambiguity pressure, but the decay threshold has not been reached yet.",
                next_safe_cycle_decay_count,
                f"{next_safe_cycle_decay_count} of {_SAFE_CYCLE_DECAY_THRESHOLD} safe non-referential cycles have been observed toward governance relaxation.",
                "safe_nonreferential_cycles",
            )

        return (
            previous_policy,
            "held",
            f"Control governance remains in {previous_policy.tier} mode until a referential request is resolved with an explicit anchor or enough safe non-referential cycles are observed.",
            "hold_until_explicit_anchor_resolution",
            "awaiting_explicit_anchor_resolution",
            "Recent ambiguity pressure has eased, but governance remains active because no explicit anchored referential resolution or sufficient safe-cycle decay has been observed yet.",
            0,
            "No safe-cycle decay progress was recorded in the latest attempt, so governance remains held.",
            "none",
        )

    direction = _tier_transition_direction(previous_policy.tier, base_policy.tier)
    return (
        base_policy,
        direction,
        _tier_transition_summary(previous_tier=previous_policy.tier, current_tier=base_policy.tier, direction=direction),
        "baseline",
        "standard",
        "No elevated referential governance remains active.",
        0,
        "No elevated governance is active, so no decay tracking is required.",
        "none",
    )


def _anchored_cooldown_policy(*, previous_tier: str) -> ControlGovernancePolicy:
    if previous_tier == "strict":
        return ControlGovernancePolicy(
            tier="elevated",
            interpretation_safety_mode="explicit_referential_anchor_required",
            requires_explicit_referential_anchor=True,
            reason="A recent anchored referential resolution reduced strict governance into a one-tier cooldown state, so explicit anchors are still preferred for the next cycle.",
            precheck_message="Strict referential ambiguity was resolved once with an explicit anchor. Governance remains elevated during cooldown, so keep the next referential request explicit as well.",
            preview_hint="Referential governance has relaxed from strict to elevated after an anchored resolution, but the next cycle should still keep commit/node selectors explicit.",
            next_actions=("provide_explicit_anchor", "review_explicit_anchor"),
        )
    return ControlGovernancePolicy()




def _safe_cycle_decay_policy(*, previous_tier: str) -> ControlGovernancePolicy:
    if previous_tier == "strict":
        return ControlGovernancePolicy(
            tier="elevated",
            interpretation_safety_mode="explicit_referential_anchor_required",
            requires_explicit_referential_anchor=True,
            reason="Recent safe non-referential cycles reduced ambiguity pressure, so strict governance has relaxed into elevated cooldown mode.",
            precheck_message="Recent safe non-referential cycles reduced strict governance into elevated cooldown mode. Prefer explicit anchors for the next referential request while ambiguity pressure finishes decaying.",
            preview_hint="Referential governance has relaxed from strict to elevated after sustained safe non-referential cycles, but the next referential request should still stay explicit.",
            next_actions=("provide_explicit_anchor", "continue_nonreferential_changes_if_possible"),
        )
    return ControlGovernancePolicy()


def _pressure_score_floor_for_tier(tier: str) -> int:
    if tier == "strict":
        return _STRICT_PRESSURE_SCORE
    if tier == "elevated":
        return _ELEVATED_PRESSURE_SCORE
    return 0


def _pressure_band_for_score(score: int) -> str:
    if score >= _STRICT_PRESSURE_SCORE:
        return "strict"
    if score >= _ELEVATED_PRESSURE_SCORE:
        return "elevated"
    return "standard"


def _apply_pressure_transition(
    *,
    previous_score: int,
    previous_policy: ControlGovernancePolicy,
    current_policy: ControlGovernancePolicy,
    transition_rule: str,
    resolution_state: str,
) -> tuple[int, str, str, str]:
    next_score = previous_score
    if transition_rule == "repeat_confirmation_threshold":
        base_floor = _pressure_score_floor_for_tier(current_policy.tier)
        if current_policy.tier == previous_policy.tier and current_policy.tier in {"elevated", "strict"}:
            next_score = min(_PRESSURE_SCORE_MAX, max(previous_score + 1, base_floor))
        else:
            next_score = max(previous_score, base_floor)
        transition = "escalating_or_sustained_repeat_pressure"
    elif transition_rule == "anchored_resolution_cooldown":
        next_score = max(_pressure_score_floor_for_tier(current_policy.tier), previous_score - 2)
        transition = "anchored_relief_step"
    elif transition_rule == "anchored_resolution_cleared":
        next_score = 0
        transition = "anchored_relief_cleared"
    elif transition_rule == "safe_cycle_decay_threshold":
        if current_policy.tier == "standard":
            next_score = 0
        else:
            next_score = max(_pressure_score_floor_for_tier(current_policy.tier), previous_score - 2)
        transition = "safe_cycle_relief_step" if current_policy.tier != "standard" else "safe_cycle_relief_cleared"
    elif transition_rule == "safe_cycle_decay_progress":
        next_score = max(_pressure_score_floor_for_tier(previous_policy.tier), previous_score - 1)
        transition = "safe_cycle_relief_progress"
    elif transition_rule == "hold_until_explicit_anchor_resolution":
        next_score = max(previous_score, _pressure_score_floor_for_tier(previous_policy.tier))
        transition = "held_until_resolution"
    else:
        next_score = _pressure_score_floor_for_tier(current_policy.tier)
        transition = "baseline"

    band = _pressure_band_for_score(next_score)
    if transition == "escalating_or_sustained_repeat_pressure":
        summary = f"Ambiguity pressure is now {next_score} ({band}) after repeated confirmation pressure in the current cycle."
    elif transition == "anchored_relief_step":
        summary = f"Ambiguity pressure dropped from {previous_score} to {next_score} after an explicit anchored referential resolution."
    elif transition == "anchored_relief_cleared":
        summary = "Ambiguity pressure cleared fully after an explicit anchored referential resolution."
    elif transition == "safe_cycle_relief_step":
        summary = f"Ambiguity pressure dropped from {previous_score} to {next_score} after enough safe non-referential cycles to relax one governance tier."
    elif transition == "safe_cycle_relief_cleared":
        summary = "Ambiguity pressure cleared fully after enough safe non-referential cycles."
    elif transition == "safe_cycle_relief_progress":
        summary = f"Ambiguity pressure is easing within the current tier ({previous_score} -> {next_score}) while safe-cycle decay progresses."
    elif transition == "held_until_resolution":
        summary = f"Ambiguity pressure remains at {next_score} ({band}) until an explicit anchor resolution or enough safe-cycle decay is observed."
    else:
        summary = f"Ambiguity pressure is {next_score} ({band})."
    return next_score, band, transition, summary


def _is_safe_cycle_decay_candidate(latest_attempt: RevisionAttemptSummary) -> bool:
    if latest_attempt.reason_code in _ANCHORED_RESOLUTION_REASON_CODES:
        return False
    return (
        latest_attempt.reason_code in {"DESIGNER-READY-FOR-APPROVAL", "DESIGNER-CONFIRMATION-REQUIRED"}
        and latest_attempt.outcome in {"ready_for_approval", "confirmation_required"}
    )


def _policy_defaults_for_tier(tier: str) -> ControlGovernancePolicy:
    if tier == "strict":
        return ControlGovernancePolicy(
            tier="strict",
            interpretation_safety_mode="explicit_referential_anchor_required",
            requires_explicit_referential_anchor=True,
            reason="Three or more closely related confirmation cycles were observed, so referential auto-resolution has moved into strict governance mode.",
            precheck_message="Repeated referential ambiguity has triggered strict governance mode. Provide an explicit commit anchor, explicit node target, or explicit non-latest selector before approval can continue safely.",
            preview_hint="Strict referential governance is active. The next safe step is to restate the request with a stronger anchor instead of relying on 'last change' style language.",
            next_actions=("provide_explicit_anchor", "restate_request_with_stronger_selector"),
        )
    if tier == "elevated":
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


def _tier_transition_summary(*, previous_tier: str, current_tier: str, direction: str) -> str:
    if direction == "escalated":
        return f"Control governance escalated from {previous_tier} to {current_tier} based on recent repeated confirmation patterns."
    if direction == "deescalated":
        return f"Control governance deescalated from {previous_tier} to {current_tier} after recent repeated confirmation pressure eased."
    if direction == "held":
        return f"Control governance remains in {current_tier} mode until an explicit anchored referential resolution is observed."
    return f"Control governance remains in {current_tier} mode."
