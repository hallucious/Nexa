from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.contracts.designer_contract import (
    CHANGE_SCOPE_LEVELS,
    PROPOSAL_CONTROL_ACTIONS,
    PROPOSAL_CONTROL_ATTEMPT_OUTCOMES,
    PROPOSAL_CONTROL_STAGES,
    PROPOSAL_CONTROL_TERMINAL_STATUSES,
    TARGET_SCOPE_MODES,
)
from src.designer.models.designer_intent import ConstraintSet, ObjectiveSpec

_SELECTION_MODES = {"none", "node", "edge", "output", "subgraph", "whole_circuit"}
_APPROVAL_STATUSES = {"not_started", "pending", "approved", "rejected", "committed"}
_STORAGE_ROLES = {"working_save", "commit_snapshot", "none"}
_RESOURCE_STATUSES = {"available", "unavailable", "unknown"}


@dataclass(frozen=True)
class ResourceAvailability:
    id: str
    availability_status: str = "available"
    version: str | None = None
    tags: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ResourceAvailability.id must be non-empty")
        if self.availability_status not in _RESOURCE_STATUSES:
            raise ValueError(f"Unsupported availability_status: {self.availability_status}")


@dataclass(frozen=True)
class WorkingSaveReality:
    mode: str = "existing_draft"
    savefile_ref: str | None = None
    current_revision: str | None = None
    circuit_summary: str = ""
    node_list: tuple[str, ...] = ()
    edge_list: tuple[str, ...] = ()
    output_list: tuple[str, ...] = ()
    prompt_refs: tuple[str, ...] = ()
    provider_refs: tuple[str, ...] = ()
    plugin_refs: tuple[str, ...] = ()
    draft_validity_status: str = "unknown"

    def __post_init__(self) -> None:
        if self.mode not in {"existing_draft", "empty_draft"}:
            raise ValueError(f"Unsupported WorkingSaveReality.mode: {self.mode}")
        if self.mode == "existing_draft" and self.savefile_ref is None:
            raise ValueError("WorkingSaveReality.savefile_ref is required for existing_draft mode")


@dataclass(frozen=True)
class CurrentSelectionState:
    selection_mode: str = "none"
    selected_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.selection_mode not in _SELECTION_MODES:
            raise ValueError(f"Unsupported selection_mode: {self.selection_mode}")


@dataclass(frozen=True)
class SessionTargetScope:
    mode: str
    touch_budget: str = "bounded"
    allowed_node_refs: tuple[str, ...] = ()
    allowed_edge_refs: tuple[str, ...] = ()
    allowed_output_refs: tuple[str, ...] = ()
    destructive_edit_allowed: bool = False

    def __post_init__(self) -> None:
        if self.mode not in TARGET_SCOPE_MODES:
            raise ValueError(f"Unsupported SessionTargetScope.mode: {self.mode}")
        if self.touch_budget not in CHANGE_SCOPE_LEVELS:
            raise ValueError(f"Unsupported SessionTargetScope.touch_budget: {self.touch_budget}")


@dataclass(frozen=True)
class AvailableResources:
    prompts: tuple[ResourceAvailability, ...] = ()
    providers: tuple[ResourceAvailability, ...] = ()
    plugins: tuple[ResourceAvailability, ...] = ()


@dataclass(frozen=True)
class CurrentFindingsState:
    blocking_findings: tuple[str, ...] = ()
    warning_findings: tuple[str, ...] = ()
    confirmation_findings: tuple[str, ...] = ()
    finding_summary: str = ""


@dataclass(frozen=True)
class CurrentRisksState:
    risk_flags: tuple[str, ...] = ()
    severity_summary: str = ""
    unresolved_high_risks: tuple[str, ...] = ()


@dataclass(frozen=True)
class RevisionAttemptSummary:
    attempt_index: int
    stage: str
    outcome: str
    reason_code: str
    message: str

    def __post_init__(self) -> None:
        if self.attempt_index < 1:
            raise ValueError("RevisionAttemptSummary.attempt_index must be >= 1")
        if self.stage not in PROPOSAL_CONTROL_STAGES:
            raise ValueError(f"Unsupported RevisionAttemptSummary.stage: {self.stage}")
        if self.outcome not in PROPOSAL_CONTROL_ATTEMPT_OUTCOMES:
            raise ValueError(f"Unsupported RevisionAttemptSummary.outcome: {self.outcome}")
        if not self.reason_code.strip():
            raise ValueError("RevisionAttemptSummary.reason_code must be non-empty")
        if not self.message.strip():
            raise ValueError("RevisionAttemptSummary.message must be non-empty")


@dataclass(frozen=True)
class RevisionState:
    revision_index: int = 0
    based_on_intent_id: str | None = None
    based_on_patch_id: str | None = None
    prior_rejection_reasons: tuple[str, ...] = ()
    retry_reason: str | None = None
    user_corrections: tuple[str, ...] = ()
    last_control_action: str | None = None
    last_terminal_status: str | None = None
    attempt_history: tuple[RevisionAttemptSummary, ...] = ()

    def __post_init__(self) -> None:
        if self.revision_index < 0:
            raise ValueError("RevisionState.revision_index must be non-negative")
        if self.last_control_action is not None and self.last_control_action not in PROPOSAL_CONTROL_ACTIONS:
            raise ValueError(f"Unsupported RevisionState.last_control_action: {self.last_control_action}")
        if self.last_terminal_status is not None and self.last_terminal_status not in PROPOSAL_CONTROL_TERMINAL_STATUSES:
            raise ValueError(f"Unsupported RevisionState.last_terminal_status: {self.last_terminal_status}")


@dataclass(frozen=True)
class ApprovalState:
    approval_required: bool = True
    approval_status: str = "not_started"
    confirmation_required: bool = False
    blocking_before_commit: bool = False

    def __post_init__(self) -> None:
        if self.approval_status not in _APPROVAL_STATUSES:
            raise ValueError(f"Unsupported approval_status: {self.approval_status}")


@dataclass(frozen=True)
class ConversationContext:
    user_request_text: str
    clarified_interpretation: str | None = None
    unresolved_questions: tuple[str, ...] = ()
    explicit_user_preferences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.user_request_text.strip():
            raise ValueError("ConversationContext.user_request_text must be non-empty")


@dataclass(frozen=True)
class OutputContract:
    required_primary_output: str = "normalized_intent"
    allowed_secondary_outputs: tuple[str, ...] = ("patch_plan", "explanation", "ambiguity_report", "risk_report")
    preview_required: bool = True


@dataclass(frozen=True)
class ForbiddenAuthority:
    may_commit_directly: bool = False
    may_redefine_engine_contracts: bool = False
    may_bypass_precheck: bool = False
    may_bypass_preview: bool = False
    may_bypass_approval: bool = False
    may_mutate_committed_truth_directly: bool = False


@dataclass(frozen=True)
class DesignerSessionStateCard:
    card_version: str
    session_id: str
    storage_role: str
    current_working_save: WorkingSaveReality
    current_selection: CurrentSelectionState
    target_scope: SessionTargetScope
    available_resources: AvailableResources
    objective: ObjectiveSpec
    constraints: ConstraintSet = field(default_factory=ConstraintSet)
    current_findings: CurrentFindingsState = field(default_factory=CurrentFindingsState)
    current_risks: CurrentRisksState = field(default_factory=CurrentRisksState)
    revision_state: RevisionState = field(default_factory=RevisionState)
    approval_state: ApprovalState = field(default_factory=ApprovalState)
    conversation_context: ConversationContext = field(default_factory=lambda: ConversationContext(user_request_text="(unspecified request)"))
    output_contract: OutputContract = field(default_factory=OutputContract)
    forbidden_authority: ForbiddenAuthority = field(default_factory=ForbiddenAuthority)
    notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.card_version.strip():
            raise ValueError("DesignerSessionStateCard.card_version must be non-empty")
        if not self.session_id.strip():
            raise ValueError("DesignerSessionStateCard.session_id must be non-empty")
        if self.storage_role not in _STORAGE_ROLES:
            raise ValueError(f"Unsupported storage_role: {self.storage_role}")
        if self.storage_role == "working_save" and self.target_scope.mode == "read_only":
            return
        if self.storage_role == "commit_snapshot" and self.target_scope.mode not in {"read_only", "existing_circuit", "node_only", "subgraph_only"}:
            raise ValueError("commit_snapshot storage_role does not support new_circuit scope")
