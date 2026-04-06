from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.designer_contract import DESIGNER_INTENT_CATEGORIES


@dataclass(frozen=True)
class SemanticTargetDescriptor:
    kind: str = "unspecified"
    label_hint: str | None = None
    role_hint: str | None = None
    position_hint: str | None = None
    raw_reference_text: str | None = None


@dataclass(frozen=True)
class SemanticResourceDescriptor:
    resource_type: str
    family: str | None = None
    label_hint: str | None = None
    capability_hint: str | None = None
    raw_reference_text: str | None = None


@dataclass(frozen=True)
class SemanticActionCandidate:
    action_type: str
    target_node_descriptor: SemanticTargetDescriptor | None = None
    provider_descriptor: SemanticResourceDescriptor | None = None
    plugin_descriptor: SemanticResourceDescriptor | None = None
    prompt_descriptor: SemanticResourceDescriptor | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.action_type.strip():
            raise ValueError("SemanticActionCandidate.action_type must be non-empty")


@dataclass(frozen=True)
class SemanticIntent:
    semantic_intent_id: str
    user_request_text: str
    effective_request_text: str
    category: str
    action_candidates: tuple[SemanticActionCandidate, ...] = ()
    confidence_hint: float = 1.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.semantic_intent_id.strip():
            raise ValueError("SemanticIntent.semantic_intent_id must be non-empty")
        if not self.user_request_text.strip():
            raise ValueError("SemanticIntent.user_request_text must be non-empty")
        if not self.effective_request_text.strip():
            raise ValueError("SemanticIntent.effective_request_text must be non-empty")
        if self.category not in DESIGNER_INTENT_CATEGORIES:
            raise ValueError(f"Unsupported semantic intent category: {self.category}")
        if not 0.0 <= self.confidence_hint <= 1.0:
            raise ValueError("SemanticIntent.confidence_hint must be between 0.0 and 1.0")
