from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.contracts.designer_contract import (
    NODE_CHANGE_TYPES,
    NODE_CRITICALITIES,
    PREVIEW_MODES,
    SUMMARY_OVERALL_STATUSES,
    SUMMARY_PROPOSAL_TYPES,
)


@dataclass(frozen=True)
class SummaryCard:
    title: str
    one_sentence_summary: str
    proposal_type: str
    change_scope: str
    touched_node_count: int
    touched_edge_count: int
    touched_output_count: int
    overall_status: str = "safe_to_preview"
    user_action_hint: str = ""

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("SummaryCard.title must be non-empty")
        if not self.one_sentence_summary.strip():
            raise ValueError("SummaryCard.one_sentence_summary must be non-empty")
        if self.proposal_type not in SUMMARY_PROPOSAL_TYPES:
            raise ValueError(f"Unsupported SummaryCard.proposal_type: {self.proposal_type}")
        if self.change_scope not in {"minimal", "bounded", "broad"}:
            raise ValueError(f"Unsupported SummaryCard.change_scope: {self.change_scope}")
        if self.overall_status not in SUMMARY_OVERALL_STATUSES:
            raise ValueError(f"Unsupported SummaryCard.overall_status: {self.overall_status}")
        if min(self.touched_node_count, self.touched_edge_count, self.touched_output_count) < 0:
            raise ValueError("SummaryCard touched counts must be non-negative")


@dataclass(frozen=True)
class EdgeSummary:
    from_node: str
    to_node: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.from_node.strip():
            raise ValueError("EdgeSummary.from_node must be non-empty")
        if not self.to_node.strip():
            raise ValueError("EdgeSummary.to_node must be non-empty")


@dataclass(frozen=True)
class StructuralPreview:
    before_exists: bool
    before_node_count: int = 0
    after_node_count: int = 0
    before_edge_count: int = 0
    after_edge_count: int = 0
    added_nodes: tuple[str, ...] = ()
    removed_nodes: tuple[str, ...] = ()
    modified_nodes: tuple[str, ...] = ()
    added_edges: tuple[EdgeSummary, ...] = ()
    removed_edges: tuple[EdgeSummary, ...] = ()
    changed_outputs: tuple[str, ...] = ()
    structural_delta_summary: str = ""

    def __post_init__(self) -> None:
        if min(
            self.before_node_count,
            self.after_node_count,
            self.before_edge_count,
            self.after_edge_count,
        ) < 0:
            raise ValueError("StructuralPreview counts must be non-negative")


@dataclass(frozen=True)
class NodeChangeCard:
    node_ref: str
    change_type: str
    before_summary: str | None = None
    after_summary: str | None = None
    why_it_changed: str = ""
    expected_effect: str = ""
    criticality: str = "low"

    def __post_init__(self) -> None:
        if not self.node_ref.strip():
            raise ValueError("NodeChangeCard.node_ref must be non-empty")
        if self.change_type not in NODE_CHANGE_TYPES:
            raise ValueError(f"Unsupported NodeChangeCard.change_type: {self.change_type}")
        if not self.why_it_changed.strip():
            raise ValueError("NodeChangeCard.why_it_changed must be non-empty")
        if not self.expected_effect.strip():
            raise ValueError("NodeChangeCard.expected_effect must be non-empty")
        if self.criticality not in NODE_CRITICALITIES:
            raise ValueError(f"Unsupported NodeChangeCard.criticality: {self.criticality}")


@dataclass(frozen=True)
class NodeChangePreview:
    cards: tuple[NodeChangeCard, ...] = ()


@dataclass(frozen=True)
class EdgeChangeCard:
    from_node: str
    to_node: str
    change_type: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.from_node.strip() or not self.to_node.strip():
            raise ValueError("EdgeChangeCard endpoints must be non-empty")
        if self.change_type not in {"created", "deleted", "modified", "unchanged"}:
            raise ValueError(f"Unsupported EdgeChangeCard.change_type: {self.change_type}")


@dataclass(frozen=True)
class EdgeChangePreview:
    cards: tuple[EdgeChangeCard, ...] = ()


@dataclass(frozen=True)
class OutputChangeCard:
    output_ref: str
    change_type: str
    before_summary: str | None = None
    after_summary: str | None = None

    def __post_init__(self) -> None:
        if not self.output_ref.strip():
            raise ValueError("OutputChangeCard.output_ref must be non-empty")
        if self.change_type not in {"created", "deleted", "modified", "unchanged"}:
            raise ValueError(f"Unsupported OutputChangeCard.change_type: {self.change_type}")


@dataclass(frozen=True)
class OutputChangePreview:
    cards: tuple[OutputChangeCard, ...] = ()


@dataclass(frozen=True)
class BehaviorChangePreview:
    summary: str = ""
    expected_effects: tuple[str, ...] = ()
    possible_regressions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RiskPreview:
    summary: str = ""
    risks: tuple[str, ...] = ()
    requires_confirmation: bool = False


@dataclass(frozen=True)
class CostPreview:
    cost_summary: str = ""
    estimated_cost_change: str | None = None
    complexity_change: str | None = None


@dataclass(frozen=True)
class AssumptionPreview:
    assumptions: tuple[str, ...] = ()
    default_choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfirmationPreview:
    required_confirmations: tuple[str, ...] = ()
    auto_commit_allowed: bool = False


@dataclass(frozen=True)
class GraphViewModel:
    node_count: int = 0
    edge_count: int = 0
    annotations: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.node_count < 0 or self.edge_count < 0:
            raise ValueError("GraphViewModel counts must be non-negative")


@dataclass(frozen=True)
class CircuitDraftPreview:
    preview_id: str
    intent_ref: str
    patch_ref: str
    precheck_ref: str
    preview_mode: str
    summary_card: SummaryCard
    structural_preview: StructuralPreview
    node_change_preview: NodeChangePreview = field(default_factory=NodeChangePreview)
    edge_change_preview: EdgeChangePreview = field(default_factory=EdgeChangePreview)
    output_change_preview: OutputChangePreview = field(default_factory=OutputChangePreview)
    behavior_change_preview: BehaviorChangePreview = field(default_factory=BehaviorChangePreview)
    risk_preview: RiskPreview = field(default_factory=RiskPreview)
    cost_preview: CostPreview = field(default_factory=CostPreview)
    assumption_preview: AssumptionPreview = field(default_factory=AssumptionPreview)
    confirmation_preview: ConfirmationPreview = field(default_factory=ConfirmationPreview)
    graph_view_model: GraphViewModel | None = None
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.preview_id.strip():
            raise ValueError("CircuitDraftPreview.preview_id must be non-empty")
        if not self.intent_ref.strip():
            raise ValueError("CircuitDraftPreview.intent_ref must be non-empty")
        if not self.patch_ref.strip():
            raise ValueError("CircuitDraftPreview.patch_ref must be non-empty")
        if not self.precheck_ref.strip():
            raise ValueError("CircuitDraftPreview.precheck_ref must be non-empty")
        if self.preview_mode not in PREVIEW_MODES:
            raise ValueError(f"Unsupported CircuitDraftPreview.preview_mode: {self.preview_mode}")
        removed_nodes = set(self.structural_preview.removed_nodes)
        deleted_cards = {card.node_ref for card in self.node_change_preview.cards if card.change_type == "deleted"}
        if deleted_cards - removed_nodes:
            raise ValueError(
                "CircuitDraftPreview.structural_preview.removed_nodes must include all deleted node change cards"
            )
        if self.summary_card.touched_node_count < len(self.node_change_preview.cards):
            raise ValueError("SummaryCard.touched_node_count cannot be smaller than the number of node change cards")
        if self.summary_card.touched_edge_count < len(self.edge_change_preview.cards):
            raise ValueError("SummaryCard.touched_edge_count cannot be smaller than the number of edge change cards")
        if self.summary_card.touched_output_count < len(self.output_change_preview.cards):
            raise ValueError("SummaryCard.touched_output_count cannot be smaller than the number of output change cards")
