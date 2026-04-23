from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.contracts.designer_contract import (
    ACTION_TYPES,
    ASSUMPTION_SEVERITIES,
    CHANGE_SCOPE_LEVELS,
    DESIGNER_INTENT_CATEGORIES,
    RISK_SEVERITIES,
    TARGET_SCOPE_MODES,
)


@dataclass(frozen=True)
class TargetScope:
    mode: str
    savefile_ref: str | None = None
    node_refs: tuple[str, ...] = ()
    edge_refs: tuple[str, ...] = ()
    max_change_scope: str = "bounded"

    def __post_init__(self) -> None:
        if self.mode not in TARGET_SCOPE_MODES:
            raise ValueError(f"Unsupported target scope mode: {self.mode}")
        if self.max_change_scope not in CHANGE_SCOPE_LEVELS:
            raise ValueError(f"Unsupported max_change_scope: {self.max_change_scope}")
        if self.mode == "new_circuit" and self.savefile_ref is not None:
            raise ValueError("TargetScope.savefile_ref must be omitted for new_circuit mode")
        if self.mode == "read_only" and self.max_change_scope != "minimal":
            raise ValueError("TargetScope.max_change_scope must be 'minimal' for read_only mode")


@dataclass(frozen=True)
class ObjectiveSpec:
    primary_goal: str
    secondary_goals: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    preferred_behavior: str | None = None

    def __post_init__(self) -> None:
        if not self.primary_goal.strip():
            raise ValueError("ObjectiveSpec.primary_goal must be non-empty")


@dataclass(frozen=True)
class ConstraintSet:
    cost_limit: str | None = None
    speed_priority: str | None = None
    quality_priority: str | None = None
    determinism_preference: str | None = None
    provider_preferences: tuple[str, ...] = ()
    provider_restrictions: tuple[str, ...] = ()
    plugin_preferences: tuple[str, ...] = ()
    plugin_restrictions: tuple[str, ...] = ()
    human_review_required: bool = False
    safety_level: str | None = None
    output_requirements: tuple[str, ...] = ()
    forbidden_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionSpec:
    action_type: str
    target_ref: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.action_type not in ACTION_TYPES:
            raise ValueError(f"Unsupported action_type: {self.action_type}")
        if not self.rationale.strip():
            raise ValueError("ActionSpec.rationale must be non-empty")


@dataclass(frozen=True)
class AssumptionSpec:
    text: str
    severity: str = "low"
    user_visible: bool = True

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("AssumptionSpec.text must be non-empty")
        if self.severity not in ASSUMPTION_SEVERITIES:
            raise ValueError(f"Unsupported assumption severity: {self.severity}")


@dataclass(frozen=True)
class AmbiguityFlag:
    type: str
    description: str

    def __post_init__(self) -> None:
        if not self.type.strip():
            raise ValueError("AmbiguityFlag.type must be non-empty")
        if not self.description.strip():
            raise ValueError("AmbiguityFlag.description must be non-empty")


@dataclass(frozen=True)
class RiskFlag:
    type: str
    severity: str
    description: str

    def __post_init__(self) -> None:
        if not self.type.strip():
            raise ValueError("RiskFlag.type must be non-empty")
        if self.severity not in RISK_SEVERITIES:
            raise ValueError(f"Unsupported risk severity: {self.severity}")
        if not self.description.strip():
            raise ValueError("RiskFlag.description must be non-empty")


@dataclass(frozen=True)
class DesignerIntent:
    intent_id: str
    category: str
    user_request_text: str
    target_scope: TargetScope
    objective: ObjectiveSpec
    constraints: ConstraintSet = field(default_factory=ConstraintSet)
    proposed_actions: tuple[ActionSpec, ...] = ()
    assumptions: tuple[AssumptionSpec, ...] = ()
    ambiguity_flags: tuple[AmbiguityFlag, ...] = ()
    risk_flags: tuple[RiskFlag, ...] = ()
    requires_user_confirmation: bool = False
    confidence: float = 1.0
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.intent_id.strip():
            raise ValueError("DesignerIntent.intent_id must be non-empty")
        if self.category not in DESIGNER_INTENT_CATEGORIES:
            raise ValueError(f"Unsupported designer intent category: {self.category}")
        if not self.user_request_text.strip():
            raise ValueError("DesignerIntent.user_request_text must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("DesignerIntent.confidence must be between 0.0 and 1.0")
        if self.category == "CREATE_CIRCUIT" and self.target_scope.mode != "new_circuit":
            raise ValueError("CREATE_CIRCUIT requires target_scope.mode='new_circuit'")
        if self.category in {"EXPLAIN_CIRCUIT", "ANALYZE_CIRCUIT"} and self.target_scope.mode != "read_only":
            raise ValueError(f"{self.category} requires target_scope.mode='read_only'")
        if self.category in {"MODIFY_CIRCUIT", "REPAIR_CIRCUIT", "OPTIMIZE_CIRCUIT"} and self.target_scope.mode in {
            "new_circuit",
            "read_only",
        }:
            raise ValueError(f"{self.category} requires a writable target_scope.mode")
        if self.ambiguity_flags and not self.requires_user_confirmation:
            raise ValueError("DesignerIntent.requires_user_confirmation must be true when ambiguity_flags are present")
        high_risk_flags = [flag for flag in self.risk_flags if flag.severity == "high"]
        if high_risk_flags and not self.requires_user_confirmation:
            raise ValueError("DesignerIntent.requires_user_confirmation must be true when high-severity risks are present")
