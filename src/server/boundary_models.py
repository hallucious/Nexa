from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from src.automation.trigger_model import DEFAULT_TRIGGER_SOURCE, normalize_trigger_source


def _normalize_boundary_trigger_source(value: str | None) -> str:
    normalized = (value or DEFAULT_TRIGGER_SOURCE).strip().lower()
    if normalized == "webhook":
        normalized = "event"
    return normalize_trigger_source(normalized)

LaunchDecision = Literal["accepted", "rejected"]
BoundaryStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
    "paused",
    "partial",
    "cancelled",
    "unknown",
]
ResultState = Literal["not_ready", "ready_success", "ready_partial", "ready_failure"]
ValidationOverallStatus = Literal["passed", "passed_with_warnings", "blocked"]

_ALLOWED_BOUNDARY_STATUSES = {
    "queued",
    "running",
    "completed",
    "failed",
    "paused",
    "partial",
    "cancelled",
    "unknown",
}
_ALLOWED_RESULT_STATES = {"not_ready", "ready_success", "ready_partial", "ready_failure"}
_ALLOWED_VALIDATION_OVERALL_STATUSES = {"passed", "passed_with_warnings", "blocked"}


@dataclass(frozen=True)
class EngineExecutionTarget:
    target_type: str
    target_ref: str

    def __post_init__(self) -> None:
        if not self.target_type:
            raise ValueError("EngineExecutionTarget.target_type must be non-empty")
        if not self.target_ref:
            raise ValueError("EngineExecutionTarget.target_ref must be non-empty")


@dataclass(frozen=True)
class EngineRuntimeOptions:
    strict_determinism: bool = False
    trigger_source: str = DEFAULT_TRIGGER_SOURCE
    automation_id: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "trigger_source", _normalize_boundary_trigger_source(self.trigger_source))
        if self.automation_id is not None and not self.automation_id:
            raise ValueError("EngineRuntimeOptions.automation_id must be non-empty when provided")


@dataclass(frozen=True)
class EngineCorrelationContext:
    auth_context_ref: Optional[str] = None
    requested_by_user_ref: Optional[str] = None
    correlation_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_metadata, dict):
            raise TypeError("EngineCorrelationContext.correlation_metadata must be a dict")
        if self.auth_context_ref is not None and not self.auth_context_ref:
            raise ValueError("EngineCorrelationContext.auth_context_ref must be non-empty when provided")
        if self.requested_by_user_ref is not None and not self.requested_by_user_ref:
            raise ValueError("EngineCorrelationContext.requested_by_user_ref must be non-empty when provided")


@dataclass(frozen=True)
class EngineRunLaunchRequest:
    run_request_id: str
    workspace_ref: str
    execution_target: EngineExecutionTarget
    input_payload: Any = None
    runtime_options: EngineRuntimeOptions = field(default_factory=EngineRuntimeOptions)
    correlation_context: EngineCorrelationContext = field(default_factory=EngineCorrelationContext)
    auth_context_ref: Optional[str] = None
    requested_by_user_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_request_id:
            raise ValueError("EngineRunLaunchRequest.run_request_id must be non-empty")
        if not self.workspace_ref:
            raise ValueError("EngineRunLaunchRequest.workspace_ref must be non-empty")
        if self.auth_context_ref is not None and not self.auth_context_ref:
            raise ValueError("EngineRunLaunchRequest.auth_context_ref must be non-empty when provided")
        if self.requested_by_user_ref is not None and not self.requested_by_user_ref:
            raise ValueError("EngineRunLaunchRequest.requested_by_user_ref must be non-empty when provided")


@dataclass(frozen=True)
class EngineExecutionBinding:
    circuit: dict[str, Any]
    state: dict[str, Any]
    strict_determinism: bool = False
    trigger_source: str = DEFAULT_TRIGGER_SOURCE
    automation_id: Optional[str] = None
    launch_metadata: dict[str, Any] = field(default_factory=dict)
    input_payload: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.circuit, dict):
            raise TypeError("EngineExecutionBinding.circuit must be a dict")
        if not isinstance(self.state, dict):
            raise TypeError("EngineExecutionBinding.state must be a dict")
        if not isinstance(self.launch_metadata, dict):
            raise TypeError("EngineExecutionBinding.launch_metadata must be a dict")
        object.__setattr__(self, "trigger_source", _normalize_boundary_trigger_source(self.trigger_source))
        if self.automation_id is not None and not self.automation_id:
            raise ValueError("EngineExecutionBinding.automation_id must be non-empty when provided")

    def to_circuit_runner_kwargs(self) -> dict[str, Any]:
        return {
            "strict_determinism": self.strict_determinism,
            "trigger_source": self.trigger_source,
            "automation_id": self.automation_id,
        }


@dataclass(frozen=True)
class EngineValidationFinding:
    code: str
    category: str
    severity: str
    blocking: bool
    message: str
    location: Optional[str] = None
    hint: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("EngineValidationFinding.code must be non-empty")
        if not self.category:
            raise ValueError("EngineValidationFinding.category must be non-empty")
        if not self.severity:
            raise ValueError("EngineValidationFinding.severity must be non-empty")
        if not self.message:
            raise ValueError("EngineValidationFinding.message must be non-empty")


@dataclass(frozen=True)
class EngineValidationEnvelope:
    overall_status: ValidationOverallStatus
    blocking_count: int
    warning_count: int
    findings: list[EngineValidationFinding] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.overall_status not in _ALLOWED_VALIDATION_OVERALL_STATUSES:
            raise ValueError(f"Unsupported validation overall_status: {self.overall_status}")
        if self.blocking_count < 0:
            raise ValueError("EngineValidationEnvelope.blocking_count must be >= 0")
        if self.warning_count < 0:
            raise ValueError("EngineValidationEnvelope.warning_count must be >= 0")


@dataclass(frozen=True)
class EngineRunLaunchResponse:
    launch_status: LaunchDecision
    run_id: Optional[str] = None
    initial_status: Optional[BoundaryStatus] = None
    blocking_findings: list[EngineValidationFinding] = field(default_factory=list)
    engine_error_code: Optional[str] = None
    engine_message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.launch_status not in {"accepted", "rejected"}:
            raise ValueError(f"Unsupported launch_status: {self.launch_status}")
        if self.launch_status == "accepted" and not self.run_id:
            raise ValueError("Accepted EngineRunLaunchResponse must include run_id")
        if self.initial_status is not None and self.initial_status not in _ALLOWED_BOUNDARY_STATUSES:
            raise ValueError(f"Unsupported initial_status: {self.initial_status}")


@dataclass(frozen=True)
class EngineSignal:
    severity: str
    code: str
    message: str

    def __post_init__(self) -> None:
        if not self.severity:
            raise ValueError("EngineSignal.severity must be non-empty")
        if not self.code:
            raise ValueError("EngineSignal.code must be non-empty")
        if not self.message:
            raise ValueError("EngineSignal.message must be non-empty")


@dataclass(frozen=True)
class EngineArtifactReference:
    artifact_id: str
    artifact_type: str
    run_id: Optional[str] = None
    producer_node: Optional[str] = None
    ref: Optional[str] = None
    hash: Optional[str] = None
    lineage_refs: list[str] = field(default_factory=list)
    trace_refs: list[str] = field(default_factory=list)
    validation_status: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("EngineArtifactReference.artifact_id must be non-empty")
        if not self.artifact_type:
            raise ValueError("EngineArtifactReference.artifact_type must be non-empty")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("EngineArtifactReference.metadata must be a dict when provided")


@dataclass(frozen=True)
class EngineTraceEvent:
    event_id: str
    event_type: str
    sequence: int
    timestamp_ms: int
    node_id: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("EngineTraceEvent.event_id must be non-empty")
        if not self.event_type:
            raise ValueError("EngineTraceEvent.event_type must be non-empty")
        if self.sequence < 0:
            raise ValueError("EngineTraceEvent.sequence must be >= 0")
        if self.timestamp_ms < 0:
            raise ValueError("EngineTraceEvent.timestamp_ms must be >= 0")
        if not isinstance(self.payload, dict):
            raise TypeError("EngineTraceEvent.payload must be a dict")


@dataclass(frozen=True)
class EngineFinalOutput:
    output_key: str
    value_preview: str
    value_type: Optional[str] = None
    value_ref: Optional[str] = None
    source_node: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.output_key:
            raise ValueError("EngineFinalOutput.output_key must be non-empty")
        if not isinstance(self.value_preview, str):
            raise TypeError("EngineFinalOutput.value_preview must be a string")


@dataclass(frozen=True)
class EngineFailureInfo:
    code: str
    message: str
    location: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("EngineFailureInfo.code must be non-empty")
        if not self.message:
            raise ValueError("EngineFailureInfo.message must be non-empty")


@dataclass(frozen=True)
class EngineResultEnvelope:
    run_id: str
    final_status: BoundaryStatus
    result_state: ResultState
    result_summary: str
    final_output: Optional[EngineFinalOutput] = None
    artifact_refs: list[EngineArtifactReference] = field(default_factory=list)
    trace_ref: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    failure_info: Optional[EngineFailureInfo] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("EngineResultEnvelope.run_id must be non-empty")
        if self.final_status not in _ALLOWED_BOUNDARY_STATUSES:
            raise ValueError(f"Unsupported final_status: {self.final_status}")
        if self.result_state not in _ALLOWED_RESULT_STATES:
            raise ValueError(f"Unsupported result_state: {self.result_state}")
        if not self.result_summary:
            raise ValueError("EngineResultEnvelope.result_summary must be non-empty")
        if not isinstance(self.metrics, dict):
            raise TypeError("EngineResultEnvelope.metrics must be a dict")


@dataclass(frozen=True)
class EngineRunStatusSnapshot:
    run_id: str
    status: BoundaryStatus
    active_node_id: Optional[str] = None
    active_node_label: Optional[str] = None
    progress_percent: Optional[int] = None
    progress_summary: Optional[str] = None
    latest_signal: Optional[EngineSignal] = None
    trace_ref: Optional[str] = None
    artifact_count: int = 0
    artifact_refs: list[EngineArtifactReference] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("EngineRunStatusSnapshot.run_id must be non-empty")
        if self.status not in _ALLOWED_BOUNDARY_STATUSES:
            raise ValueError(f"Unsupported status: {self.status}")
        if self.progress_percent is not None and not 0 <= self.progress_percent <= 100:
            raise ValueError("EngineRunStatusSnapshot.progress_percent must be between 0 and 100 when provided")
        if self.artifact_count < 0:
            raise ValueError("EngineRunStatusSnapshot.artifact_count must be >= 0")
