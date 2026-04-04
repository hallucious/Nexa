from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.designer_contract import (
    PRECHECK_OVERALL_STATUSES,
    PROPOSAL_CONTROL_ACTIONS,
    PROPOSAL_CONTROL_ATTEMPT_OUTCOMES,
    PROPOSAL_CONTROL_STAGES,
    PROPOSAL_CONTROL_TERMINAL_STATUSES,
)


@dataclass(frozen=True)
class ProposalControlPolicy:
    max_normalization_attempts: int = 2
    max_revision_rounds: int = 2
    max_blocked_precheck_retries: int = 1
    allow_read_only_fallback: bool = True
    allow_confirmation_fallback: bool = True

    def __post_init__(self) -> None:
        if self.max_normalization_attempts < 1:
            raise ValueError("ProposalControlPolicy.max_normalization_attempts must be >= 1")
        if self.max_revision_rounds < 0:
            raise ValueError("ProposalControlPolicy.max_revision_rounds must be >= 0")
        if self.max_blocked_precheck_retries < 0:
            raise ValueError("ProposalControlPolicy.max_blocked_precheck_retries must be >= 0")


@dataclass(frozen=True)
class ProposalAttemptRecord:
    attempt_index: int
    stage: str
    outcome: str
    reason_code: str
    message: str

    def __post_init__(self) -> None:
        if self.attempt_index < 1:
            raise ValueError("ProposalAttemptRecord.attempt_index must be >= 1")
        if self.stage not in PROPOSAL_CONTROL_STAGES:
            raise ValueError(f"Unsupported ProposalAttemptRecord.stage: {self.stage}")
        if self.outcome not in PROPOSAL_CONTROL_ATTEMPT_OUTCOMES:
            raise ValueError(f"Unsupported ProposalAttemptRecord.outcome: {self.outcome}")
        if not self.reason_code.strip():
            raise ValueError("ProposalAttemptRecord.reason_code must be non-empty")
        if not self.message.strip():
            raise ValueError("ProposalAttemptRecord.message must be non-empty")


@dataclass(frozen=True)
class DesignerProposalControlState:
    session_id: str
    current_stage: str = "normalize"
    next_action: str = "retry_normalization"
    terminal_status: str = "in_progress"
    normalization_attempts: int = 0
    revision_rounds: int = 0
    blocked_precheck_count: int = 0
    fallback_count: int = 0
    last_precheck_status: str | None = None
    pending_reason: str | None = None
    history: tuple[ProposalAttemptRecord, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise ValueError("DesignerProposalControlState.session_id must be non-empty")
        if self.current_stage not in PROPOSAL_CONTROL_STAGES:
            raise ValueError(f"Unsupported DesignerProposalControlState.current_stage: {self.current_stage}")
        if self.next_action not in PROPOSAL_CONTROL_ACTIONS:
            raise ValueError(f"Unsupported DesignerProposalControlState.next_action: {self.next_action}")
        if self.terminal_status not in PROPOSAL_CONTROL_TERMINAL_STATUSES:
            raise ValueError(f"Unsupported DesignerProposalControlState.terminal_status: {self.terminal_status}")
        if min(self.normalization_attempts, self.revision_rounds, self.blocked_precheck_count, self.fallback_count) < 0:
            raise ValueError("DesignerProposalControlState counters must be non-negative")
        if self.last_precheck_status is not None and self.last_precheck_status not in PRECHECK_OVERALL_STATUSES:
            raise ValueError(
                f"Unsupported DesignerProposalControlState.last_precheck_status: {self.last_precheck_status}"
            )

    @property
    def revision_budget_exhausted(self) -> bool:
        return self.terminal_status == "exhausted"


@dataclass(frozen=True)
class DesignerControlledProposalResult:
    control_state: DesignerProposalControlState
    bundle: object | None = None
    explanation: str = ""
    updated_session_state_card: object | None = None

    @property
    def ready_for_approval(self) -> bool:
        return self.bundle is not None and self.control_state.terminal_status == "ready_for_approval"
