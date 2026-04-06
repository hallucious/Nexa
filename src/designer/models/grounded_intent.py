from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.designer.models.designer_intent import TargetScope
from src.designer.models.semantic_intent import SemanticIntent


@dataclass(frozen=True)
class GroundedActionCandidate:
    action_type: str
    target_ref: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_type.strip():
            raise ValueError("GroundedActionCandidate.action_type must be non-empty")


@dataclass(frozen=True)
class GroundedIntent:
    grounded_intent_id: str
    semantic_intent: SemanticIntent
    target_scope: TargetScope
    resolved_node_refs: tuple[str, ...] = ()
    matched_provider_id: str | None = None
    matched_plugin_id: str | None = None
    matched_prompt_id: str | None = None
    insert_between_parameters: dict[str, Any] = field(default_factory=dict)
    grounded_action_candidates: tuple[GroundedActionCandidate, ...] = ()
    grounding_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.grounded_intent_id.strip():
            raise ValueError("GroundedIntent.grounded_intent_id must be non-empty")
