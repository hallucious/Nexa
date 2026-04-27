from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Any

from src.ui.beginner_milestones import beginner_advanced_surfaces_unlocked, beginner_surface_active


BEGINNER_LOCKED_DEEP_SURFACE_ACTION_IDS = frozenset({
    "replay_latest",
    "open_trace",
    "open_artifacts",
    "open_diff",
    "compare_runs",
    "open_latest_commit",
    "select_rollback_target",
    "open_result_history",
})

BEGINNER_LOCKED_DEEP_SURFACE_PANEL_IDS = frozenset({
    "trace_timeline",
    "artifact",
    "diff",
    "storage",
    "result_history",
})

BEGINNER_LOCKED_DEEP_SURFACE_POLICY_TO_PANEL = {
    "trace_timeline": "trace_timeline",
    "diff_viewer": "diff",
    "artifact_viewer": "artifact",
    "storage_panel": "storage",
    "result_history": "result_history",
}

BEGINNER_LOCKED_DEEP_SURFACE_POLICY_IDS = tuple(BEGINNER_LOCKED_DEEP_SURFACE_POLICY_TO_PANEL.keys())

BEGINNER_ALLOWED_FALLBACK_PANEL_IDS = ("validation", "execution", "designer", "inspector")

BEGINNER_LOCKED_DEEP_SURFACE_REASON = "Advanced surfaces unlock after first success or explicit advanced request."


def beginner_deep_surface_gate_active(*sources: Any) -> bool:
    return beginner_surface_active(*sources) and not beginner_advanced_surfaces_unlocked(*sources)


def gate_beginner_action(action: Any, *sources: Any) -> Any:
    if beginner_deep_surface_gate_active(*sources) and action.action_id in BEGINNER_LOCKED_DEEP_SURFACE_ACTION_IDS:
        return replace(
            action,
            enabled=False,
            reason_disabled=BEGINNER_LOCKED_DEEP_SURFACE_REASON,
        )
    return action


def gate_beginner_actions(actions: Iterable[Any], *sources: Any) -> list[Any]:
    return [gate_beginner_action(action, *sources) for action in actions]



def action_blocked_by_beginner_gate(action: Any | None) -> bool:
    return bool(
        action is not None
        and not action.enabled
        and action.action_id in BEGINNER_LOCKED_DEEP_SURFACE_ACTION_IDS
        and action.reason_disabled == BEGINNER_LOCKED_DEEP_SURFACE_REASON
    )

def enabled_action_map(actions: Iterable[Any]) -> dict[str, Any]:
    return {action.action_id: action for action in actions if action.enabled}


def is_beginner_locked_action(action_id: str | None, *sources: Any) -> bool:
    return bool(
        action_id
        and action_id in BEGINNER_LOCKED_DEEP_SURFACE_ACTION_IDS
        and beginner_deep_surface_gate_active(*sources)
    )


def is_beginner_locked_panel(panel_id: str | None, *sources: Any) -> bool:
    return bool(
        panel_id
        and panel_id in BEGINNER_LOCKED_DEEP_SURFACE_PANEL_IDS
        and beginner_deep_surface_gate_active(*sources)
    )


def panel_ids_from_policy_surface_ids(surface_ids: Iterable[str]) -> set[str]:
    return {
        panel_id
        for surface_id in surface_ids
        for panel_id in [BEGINNER_LOCKED_DEEP_SURFACE_POLICY_TO_PANEL.get(str(surface_id))]
        if panel_id is not None
    }


def beginner_locked_policy_surface_ids() -> tuple[str, ...]:
    return BEGINNER_LOCKED_DEEP_SURFACE_POLICY_IDS


__all__ = [
    "BEGINNER_LOCKED_DEEP_SURFACE_ACTION_IDS",
    "BEGINNER_LOCKED_DEEP_SURFACE_PANEL_IDS",
    "BEGINNER_LOCKED_DEEP_SURFACE_POLICY_TO_PANEL",
    "BEGINNER_LOCKED_DEEP_SURFACE_POLICY_IDS",
    "BEGINNER_ALLOWED_FALLBACK_PANEL_IDS",
    "BEGINNER_LOCKED_DEEP_SURFACE_REASON",
    "beginner_deep_surface_gate_active",
    "gate_beginner_action",
    "gate_beginner_actions",
    "action_blocked_by_beginner_gate",
    "enabled_action_map",
    "is_beginner_locked_action",
    "is_beginner_locked_panel",
    "panel_ids_from_policy_surface_ids",
    "beginner_locked_policy_surface_ids",
]
