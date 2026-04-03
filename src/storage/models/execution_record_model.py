from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.contracts.execution_record_contract import (
    EXECUTION_RECORD_ALLOWED_ISSUE_CATEGORIES,
    EXECUTION_RECORD_ALLOWED_ISSUE_SEVERITIES,
    EXECUTION_RECORD_ALLOWED_NODE_OUTCOMES,
    EXECUTION_RECORD_ALLOWED_STATUSES,
    EXECUTION_RECORD_ALLOWED_TRIGGER_TYPES,
)


@dataclass(frozen=True)
class ExecutionMetaModel:
    run_id: str
    record_format_version: str
    created_at: str
    started_at: str
    finished_at: Optional[str] = None
    status: str = 'running'
    title: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError('ExecutionMetaModel.run_id must be non-empty')
        if not self.record_format_version:
            raise ValueError('ExecutionMetaModel.record_format_version must be non-empty')
        if not self.created_at:
            raise ValueError('ExecutionMetaModel.created_at must be non-empty')
        if not self.started_at:
            raise ValueError('ExecutionMetaModel.started_at must be non-empty')
        if self.status not in EXECUTION_RECORD_ALLOWED_STATUSES:
            raise ValueError(f"Unsupported execution record status: {self.status}")


@dataclass(frozen=True)
class ExecutionSourceModel:
    commit_id: str
    working_save_id: Optional[str] = None
    trigger_type: str = 'manual_run'
    trigger_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.commit_id:
            raise ValueError('ExecutionSourceModel.commit_id must be non-empty')
        if self.trigger_type not in EXECUTION_RECORD_ALLOWED_TRIGGER_TYPES:
            raise ValueError(f"Unsupported execution record trigger_type: {self.trigger_type}")


@dataclass(frozen=True)
class ExecutionInputModel:
    input_summary: Optional[dict[str, Any]] = None
    input_ref: Optional[str] = None
    input_hash: Optional[str] = None
    schema_summary: Optional[str] = None


@dataclass(frozen=True)
class NodeTimingCard:
    node_id: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[int] = None
    outcome: str = 'success'

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError('NodeTimingCard.node_id must be non-empty')
        if self.outcome not in EXECUTION_RECORD_ALLOWED_NODE_OUTCOMES:
            raise ValueError(f"Unsupported node timing outcome: {self.outcome}")


@dataclass(frozen=True)
class ExecutionTimelineModel:
    total_duration_ms: Optional[int] = None
    event_count: Optional[int] = None
    node_order: list[str] = field(default_factory=list)
    started_nodes: list[NodeTimingCard] = field(default_factory=list)
    completed_nodes: list[NodeTimingCard] = field(default_factory=list)
    trace_ref: Optional[str] = None
    event_stream_ref: Optional[str] = None


@dataclass(frozen=True)
class NodeResultCard:
    node_id: str
    status: str
    output_summary: Optional[str] = None
    output_type: Optional[str] = None
    output_preview: Any = None
    artifact_refs: list[str] = field(default_factory=list)
    warning_count: int = 0
    error_count: int = 0
    trace_ref: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError('NodeResultCard.node_id must be non-empty')
        if self.status not in EXECUTION_RECORD_ALLOWED_NODE_OUTCOMES:
            raise ValueError(f"Unsupported node result status: {self.status}")


@dataclass(frozen=True)
class NodeResultsModel:
    results: list[NodeResultCard] = field(default_factory=list)


@dataclass(frozen=True)
class OutputResultCard:
    output_ref: str
    source_node: Optional[str] = None
    value_summary: str = ''
    value_payload: Any = None
    value_type: Optional[str] = None
    value_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.output_ref:
            raise ValueError('OutputResultCard.output_ref must be non-empty')


@dataclass(frozen=True)
class ExecutionOutputModel:
    final_outputs: list[OutputResultCard] = field(default_factory=list)
    output_summary: Optional[str] = None
    semantic_status: str = 'normal'


@dataclass(frozen=True)
class ArtifactRecordCard:
    artifact_id: str
    artifact_type: str
    producer_node: Optional[str] = None
    hash: Optional[str] = None
    ref: Optional[str] = None
    summary: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError('ArtifactRecordCard.artifact_id must be non-empty')
        if not self.artifact_type:
            raise ValueError('ArtifactRecordCard.artifact_type must be non-empty')


@dataclass(frozen=True)
class ExecutionArtifactsModel:
    artifact_refs: list[ArtifactRecordCard] = field(default_factory=list)
    artifact_count: int = 0
    artifact_summary: Optional[str] = None


@dataclass(frozen=True)
class ExecutionIssue:
    issue_code: str
    category: str
    severity: str
    location: Optional[str] = None
    message: str = ''
    reason: Optional[str] = None
    fix_hint: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.issue_code:
            raise ValueError('ExecutionIssue.issue_code must be non-empty')
        if self.category not in EXECUTION_RECORD_ALLOWED_ISSUE_CATEGORIES:
            raise ValueError(f"Unsupported execution issue category: {self.category}")
        if self.severity not in EXECUTION_RECORD_ALLOWED_ISSUE_SEVERITIES:
            raise ValueError(f"Unsupported execution issue severity: {self.severity}")


@dataclass(frozen=True)
class RetrySummary:
    retries_attempted: int = 0
    retries_succeeded: int = 0
    retries_failed: int = 0


@dataclass(frozen=True)
class ExecutionDiagnosticsModel:
    warnings: list[ExecutionIssue] = field(default_factory=list)
    errors: list[ExecutionIssue] = field(default_factory=list)
    failure_point: Optional[str] = None
    retry_summary: Optional[RetrySummary] = None
    termination_reason: Optional[str] = None
    pause_boundary: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ExecutionObservabilityModel:
    metrics: dict[str, Any] = field(default_factory=dict)
    provider_usage_summary: Optional[dict[str, Any]] = None
    plugin_usage_summary: Optional[dict[str, Any]] = None
    trace_summary: Optional[str] = None
    observability_refs: Optional[list[str]] = None


@dataclass(frozen=True)
class ExecutionRecordModel:
    meta: ExecutionMetaModel
    source: ExecutionSourceModel
    input: ExecutionInputModel
    timeline: ExecutionTimelineModel
    node_results: NodeResultsModel
    outputs: ExecutionOutputModel
    artifacts: ExecutionArtifactsModel
    diagnostics: ExecutionDiagnosticsModel
    observability: ExecutionObservabilityModel
