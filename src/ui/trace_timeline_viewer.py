from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from src.engine.execution_event import ExecutionEvent
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.models.commit_snapshot_model import CommitSnapshotModel


@dataclass(frozen=True)
class TraceRunIdentityView:
    run_id: str | None = None
    execution_id: str | None = None
    commit_id: str | None = None
    replay_session_id: str | None = None
    title: str | None = None
    source_label: str | None = None


@dataclass(frozen=True)
class TraceTimelineSummaryView:
    total_event_count: int = 0
    visible_event_count: int = 0
    node_lane_count: int = 0
    warning_event_count: int = 0
    error_event_count: int = 0
    retry_event_count: int = 0
    artifact_link_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    top_summary_label: str | None = None


@dataclass(frozen=True)
class TraceLaneView:
    lane_id: str
    lane_type: str
    node_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    label: str = ""
    segment_count: int = 0
    status: str = "unknown"
    collapsed_by_default: bool = False


@dataclass(frozen=True)
class TraceEventView:
    event_id: str
    sequence_index: int | None = None
    event_type: str = ""
    timestamp: str = ""
    relative_offset_ms: int | None = None
    lane_ref: str | None = None
    node_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    severity: str = "info"
    short_message: str = ""
    details_preview: str | None = None
    context_read_refs: list[str] = field(default_factory=list)
    context_write_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    location_ref: str | None = None
    replay_marker: bool = False


@dataclass(frozen=True)
class TraceFocusedSliceView:
    focused_event_ids: list[str] = field(default_factory=list)
    focused_lane_ids: list[str] = field(default_factory=list)
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    summary_label: str | None = None


@dataclass(frozen=True)
class TraceReplayStateView:
    replay_active: bool = False
    replay_session_id: str | None = None
    replay_marker_count: int = 0


@dataclass(frozen=True)
class TraceFilterStateView:
    severity_filter: str | None = None
    node_filter: str | None = None
    search_query: str | None = None


@dataclass(frozen=True)
class TraceDiagnosticsView:
    missing_trace_ref: bool = False
    missing_event_stream_ref: bool = False
    partial_trace: bool = False
    warning_count: int = 0
    error_count: int = 0
    last_error_label: str | None = None


@dataclass(frozen=True)
class TraceTimelineViewerViewModel:
    source_mode: str
    storage_role: str
    timeline_status: str
    run_identity: TraceRunIdentityView = field(default_factory=TraceRunIdentityView)
    summary: TraceTimelineSummaryView = field(default_factory=TraceTimelineSummaryView)
    lanes: list[TraceLaneView] = field(default_factory=list)
    events: list[TraceEventView] = field(default_factory=list)
    focused_slice: TraceFocusedSliceView = field(default_factory=TraceFocusedSliceView)
    replay_state: TraceReplayStateView = field(default_factory=TraceReplayStateView)
    filter_state: TraceFilterStateView = field(default_factory=TraceFilterStateView)
    diagnostics: TraceDiagnosticsView = field(default_factory=TraceDiagnosticsView)
    explanation: str | None = None


def _unwrap(source):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _severity_from_event(event_type: str, payload: dict[str, Any] | None) -> str:
    payload = payload or {}
    if event_type.endswith("failed"):
        return "error"
    if "warning" in event_type:
        return "warning"
    if payload.get("status") == "failed":
        return "error"
    return "info"


def _events_from_live(live_events: Sequence[ExecutionEvent]) -> list[TraceEventView]:
    if not live_events:
        return []
    first = live_events[0].timestamp_ms
    views: list[TraceEventView] = []
    for index, event in enumerate(live_events, start=1):
        views.append(
            TraceEventView(
                event_id=f"event-{index}",
                sequence_index=index,
                event_type=event.type,
                timestamp=f"ms:{event.timestamp_ms}",
                relative_offset_ms=event.timestamp_ms - first,
                lane_ref=f"node:{event.node_id}" if event.node_id else "runtime",
                node_id=event.node_id,
                resource_type="runtime",
                severity=_severity_from_event(event.type, event.payload),
                short_message=event.type.replace("_", " "),
                details_preview=(str(event.payload) if event.payload else None),
                artifact_refs=[str(v) for v in event.payload.get("artifact_refs", [])] if isinstance(event.payload, dict) else [],
                replay_marker=False,
            )
        )
    return views


def _events_from_record(record: ExecutionRecordModel) -> list[TraceEventView]:
    views: list[TraceEventView] = []
    idx = 1
    views.append(TraceEventView(event_id=f"event-{idx}", sequence_index=idx, event_type="execution_started", timestamp=record.meta.started_at, lane_ref="runtime", resource_type="runtime", short_message="execution started"))
    idx += 1
    for card in record.timeline.started_nodes:
        views.append(TraceEventView(event_id=f"event-{idx}", sequence_index=idx, event_type="node_started", timestamp=card.started_at or record.meta.started_at, lane_ref=f"node:{card.node_id}", node_id=card.node_id, resource_type="runtime", short_message=f"node started ({card.node_id})"))
        idx += 1
    for card in record.timeline.completed_nodes:
        views.append(TraceEventView(event_id=f"event-{idx}", sequence_index=idx, event_type="node_completed", timestamp=card.finished_at or record.meta.finished_at or record.meta.started_at, lane_ref=f"node:{card.node_id}", node_id=card.node_id, resource_type="runtime", severity="error" if card.outcome == "failed" else "info", short_message=f"node completed ({card.node_id}): {card.outcome}", details_preview=getattr(card, "error", None)))
        idx += 1
    terminal = "execution_completed" if record.meta.status != "failed" else "execution_failed"
    views.append(TraceEventView(event_id=f"event-{idx}", sequence_index=idx, event_type=terminal, timestamp=record.meta.finished_at or record.meta.started_at, lane_ref="runtime", resource_type="runtime", severity="error" if record.meta.status == "failed" else "info", short_message=f"execution {record.meta.status}", replay_marker=record.source.trigger_type == "replay_run"))
    return views


def _lanes_from_record(record: ExecutionRecordModel) -> list[TraceLaneView]:
    lanes: list[TraceLaneView] = []
    statuses = {card.node_id: card.status for card in record.node_results.results}
    for node_id in record.timeline.node_order:
        lanes.append(TraceLaneView(lane_id=f"node:{node_id}", lane_type="node", node_id=node_id, label=node_id, segment_count=1, status={"success": "completed", "failed": "failed", "partial": "partial", "cancelled": "failed", "paused": "warning", "skipped": "normal"}.get(statuses.get(node_id, "unknown"), "unknown")))
    if not lanes:
        for card in record.node_results.results:
            lanes.append(TraceLaneView(lane_id=f"node:{card.node_id}", lane_type="node", node_id=card.node_id, label=card.node_id, segment_count=1, status={"success": "completed", "failed": "failed"}.get(card.status, "unknown")))
    return lanes


def _summary(events: list[TraceEventView], lanes: list[TraceLaneView], record: ExecutionRecordModel | None) -> TraceTimelineSummaryView:
    warning_count = sum(1 for event in events if event.severity == "warning")
    error_count = sum(1 for event in events if event.severity == "error")
    artifact_link_count = sum(len(event.artifact_refs) for event in events)
    started_at = record.meta.started_at if record else (events[0].timestamp if events else None)
    finished_at = record.meta.finished_at if record else (events[-1].timestamp if events else None)
    duration_seconds = None
    if record and record.timeline.total_duration_ms is not None:
        duration_seconds = round(record.timeline.total_duration_ms / 1000.0, 3)
    return TraceTimelineSummaryView(
        total_event_count=len(events),
        visible_event_count=len(events),
        node_lane_count=len(lanes),
        warning_event_count=warning_count,
        error_event_count=error_count,
        retry_event_count=sum(1 for event in events if "retry" in event.event_type),
        artifact_link_count=artifact_link_count,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        top_summary_label=f"{len(events)} events across {len(lanes)} lanes" if events or lanes else "No trace events available",
    )


def read_trace_timeline_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    execution_record: ExecutionRecordModel | None = None,
    live_events: Sequence[ExecutionEvent] | None = None,
    explanation: str | None = None,
) -> TraceTimelineViewerViewModel:
    """Build a UI-facing trace/timeline projection from engine-owned truth."""

    source = _unwrap(source)
    if isinstance(source, ExecutionRecordModel):
        execution_record = source

    if live_events:
        events = _events_from_live(live_events)
        storage_role = "execution_record" if execution_record else ("working_save" if isinstance(source, WorkingSaveModel) else ("commit_snapshot" if isinstance(source, CommitSnapshotModel) else "none"))
        lanes = sorted({TraceLaneView(lane_id=event.lane_ref or "runtime", lane_type="node" if event.node_id else "runtime", node_id=event.node_id, label=event.node_id or "runtime", segment_count=1, status="running") for event in events}, key=lambda lane: lane.lane_id)
        run_id = execution_record.meta.run_id if execution_record else live_events[0].execution_id
        return TraceTimelineViewerViewModel(
            source_mode="live_event_stream",
            storage_role=storage_role,
            timeline_status="streaming",
            run_identity=TraceRunIdentityView(run_id=run_id, execution_id=run_id, commit_id=execution_record.source.commit_id if execution_record else None, source_label="live execution"),
            summary=_summary(events, lanes, execution_record),
            lanes=lanes,
            events=events,
            focused_slice=TraceFocusedSliceView(focused_event_ids=[events[-1].event_id] if events else [], focused_lane_ids=[events[-1].lane_ref] if events and events[-1].lane_ref else [], start_timestamp=events[0].timestamp if events else None, end_timestamp=events[-1].timestamp if events else None, summary_label="Latest live slice" if events else None),
            replay_state=TraceReplayStateView(),
            diagnostics=TraceDiagnosticsView(partial_trace=True if execution_record is None else False),
            explanation=explanation,
        )

    if execution_record is not None:
        events = _events_from_record(execution_record)
        lanes = _lanes_from_record(execution_record)
        source_mode = "replay_trace" if execution_record.source.trigger_type == "replay_run" else "execution_record_trace"
        timeline_status = "streaming" if execution_record.meta.status == "running" else "finalized"
        missing_trace_ref = execution_record.timeline.trace_ref is None
        missing_event_stream_ref = execution_record.timeline.event_stream_ref is None
        replay_state = TraceReplayStateView(
            replay_active=execution_record.source.trigger_type == "replay_run",
            replay_session_id=execution_record.meta.run_id if execution_record.source.trigger_type == "replay_run" else None,
            replay_marker_count=sum(1 for event in events if event.replay_marker),
        )
        return TraceTimelineViewerViewModel(
            source_mode=source_mode,
            storage_role="execution_record",
            timeline_status=timeline_status,
            run_identity=TraceRunIdentityView(run_id=execution_record.meta.run_id, execution_id=execution_record.meta.run_id, commit_id=execution_record.source.commit_id, replay_session_id=replay_state.replay_session_id, title=execution_record.meta.title, source_label=execution_record.source.trigger_type),
            summary=_summary(events, lanes, execution_record),
            lanes=lanes,
            events=events,
            focused_slice=TraceFocusedSliceView(focused_event_ids=[events[0].event_id] if events else [], focused_lane_ids=[lanes[0].lane_id] if lanes else [], start_timestamp=events[0].timestamp if events else None, end_timestamp=events[-1].timestamp if events else None, summary_label="Trace slice" if events else None),
            replay_state=replay_state,
            diagnostics=TraceDiagnosticsView(missing_trace_ref=missing_trace_ref, missing_event_stream_ref=missing_event_stream_ref, partial_trace=missing_trace_ref or missing_event_stream_ref, warning_count=len(execution_record.diagnostics.warnings), error_count=len(execution_record.diagnostics.errors), last_error_label=execution_record.diagnostics.errors[-1].message if execution_record.diagnostics.errors else None),
            explanation=explanation,
        )

    storage_role = "working_save" if isinstance(source, WorkingSaveModel) else ("commit_snapshot" if isinstance(source, CommitSnapshotModel) else "none")
    return TraceTimelineViewerViewModel(
        source_mode="unknown",
        storage_role=storage_role,
        timeline_status="idle",
        diagnostics=TraceDiagnosticsView(missing_trace_ref=True, missing_event_stream_ref=True, partial_trace=True, last_error_label="No execution trace loaded"),
        explanation=explanation,
    )


__all__ = [
    "TraceRunIdentityView",
    "TraceTimelineSummaryView",
    "TraceLaneView",
    "TraceEventView",
    "TraceFocusedSliceView",
    "TraceReplayStateView",
    "TraceFilterStateView",
    "TraceDiagnosticsView",
    "TraceTimelineViewerViewModel",
    "read_trace_timeline_view_model",
]
