[DESIGN]
[TRACE_TIMELINE_VIEWER_VIEW_MODEL_SPEC v0.1]

1. PURPOSE

This document defines the official Trace / Timeline Viewer View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- execution event streams
- node/resource timeline progression
- trace slices
- retry/replay history
- event-to-context linkage
- event-to-artifact linkage

The Trace / Timeline Viewer is the primary temporal-observability module
of the Nexa UI shell.

It is responsible for:

- showing what happened, in what order, and when
- showing node/resource event progression over time
- showing retry/replay/event severity history
- allowing focused inspection of execution slices
- linking events to graph objects, outputs, artifacts, and diagnostics

It is not responsible for fabricating trace truth,
rewriting execution history,
or inferring missing events as if they happened.

2. POSITION IN UI ARCHITECTURE

The Trace / Timeline Viewer consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ TraceTimelineViewerViewModel
→ Trace / Timeline Viewer UI Module

The Trace / Timeline Viewer must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Trace / Timeline Viewer is a history-projection layer, not a truth layer.
3.2 Trace/history truth remains engine-owned.
3.3 Temporal ordering must come from engine evidence.
3.4 Live event streams and historical execution records must be distinguishable.
3.5 Replay history must not be conflated with original execution history.
3.6 Missing or partial trace must remain visible as partial, not silently filled in.
3.7 Timeline/UI aggregation must preserve event provenance.

4. TOP-LEVEL VIEW MODEL

TraceTimelineViewerViewModel
- source_mode: enum(
    "live_event_stream",
    "execution_record_trace",
    "replay_trace",
    "debug_trace",
    "unknown"
  )
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- timeline_status: enum(
    "idle",
    "streaming",
    "finalized",
    "partial",
    "failed",
    "unknown"
  )
- run_identity: TraceRunIdentityView
- summary: TraceTimelineSummaryView
- lanes: list[TraceLaneView]
- events: list[TraceEventView]
- focused_slice: TraceFocusedSliceView
- replay_state: TraceReplayStateView
- filter_state: TraceFilterStateView
- diagnostics: TraceDiagnosticsView
- explanation: optional string

5. FIELD SEMANTICS

5.1 source_mode
Indicates what trace surface is being shown.

Examples:
- live_event_stream
- execution_record_trace
- replay_trace
- debug_trace

5.2 storage_role
Indicates the storage layer backing the trace surface.

5.3 timeline_status
Top-level temporal stream state.

Semantics:
- idle: no current trace data loaded
- streaming: live events still arriving
- finalized: historical/live run finished and trace closed
- partial: partial trace only
- failed: trace loading/streaming failed
- unknown: cannot determine safely

5.4 run_identity
Stable run/session identity for the current trace surface.

5.5 summary
Compact counts and temporal overview.

5.6 lanes
Per-node or per-resource timeline lanes.

5.7 events
Flat event stream slice in display order.

5.8 focused_slice
Current inspected subset of the timeline.

5.9 replay_state
Replay-specific state if relevant.

5.10 filter_state
Projected filter/search/grouping state.

5.11 diagnostics
Trace completeness/load warnings/errors.

6. TRACE RUN IDENTITY VIEW

TraceRunIdentityView
- run_id: optional string
- execution_id: optional string
- commit_id: optional string
- replay_session_id: optional string
- title: optional string
- source_label: optional string

Rules:
- these identifiers must come from engine/run artifacts
- UI must not synthesize them for convenience

7. TRACE TIMELINE SUMMARY VIEW

TraceTimelineSummaryView
- total_event_count: int
- visible_event_count: int
- node_lane_count: int
- warning_event_count: int
- error_event_count: int
- retry_event_count: int
- artifact_link_count: int
- started_at: optional string
- finished_at: optional string
- duration_seconds: optional float
- top_summary_label: optional string

Purpose:
Compact overview for header/status display.

8. TRACE LANE VIEW

TraceLaneView
- lane_id: string
- lane_type: enum(
    "node",
    "resource",
    "runtime",
    "replay",
    "custom"
  )
- node_id: optional string
- resource_type: optional enum(
    "prompt",
    "provider",
    "plugin",
    "subcircuit",
    "runtime",
    "unknown"
  )
- resource_id: optional string
- label: string
- segment_count: int
- status: enum(
    "normal",
    "running",
    "completed",
    "failed",
    "partial",
    "warning",
    "unknown"
  )
- collapsed_by_default: bool

Purpose:
Represents one timeline lane such as:
- node compare_answers
- provider openai.chat
- plugin text.normalize

9. TRACE EVENT VIEW

TraceEventView
- event_id: string
- sequence_index: optional int
- event_type: string
- timestamp: string
- relative_offset_ms: optional int
- lane_ref: optional string
- node_id: optional string
- resource_type: optional enum(
    "prompt",
    "provider",
    "plugin",
    "subcircuit",
    "runtime",
    "unknown"
  )
- resource_id: optional string
- severity: enum("info", "warning", "error")
- short_message: string
- details_preview: optional string
- context_read_refs: list[string]
- context_write_refs: list[string]
- artifact_refs: list[string]
- location_ref: optional string
- replay_marker: bool

Rules:
- relative_offset_ms is a display aid, not a replacement for timestamp
- context refs must remain refs, not full context dumps by default
- replay_marker must clearly distinguish replay-generated events from original events

10. TRACE FOCUSED SLICE VIEW

TraceFocusedSliceView
- slice_mode: enum(
    "full_trace",
    "selected_node",
    "selected_resource",
    "time_window",
    "error_only",
    "custom"
  )
- start_timestamp: optional string
- end_timestamp: optional string
- selected_lane_refs: list[string]
- selected_event_ids: list[string]
- slice_summary: optional string

Purpose:
Supports focused inspection without losing global trace context.

11. TRACE REPLAY STATE VIEW

TraceReplayStateView
- replay_available: bool
- replay_status: enum(
    "not_available",
    "ready",
    "running",
    "paused",
    "completed",
    "failed",
    "unknown"
  )
- current_replay_event_id: optional string
- speed_label: optional string
- can_play: bool
- can_pause: bool
- can_resume: bool
- can_seek: bool

Rules:
- replay state must be explicit
- replay controls must not imply that original execution is being modified

12. TRACE FILTER STATE VIEW

TraceFilterStateView
- show_info: bool
- show_warnings: bool
- show_errors: bool
- show_replay_events: bool
- group_by: enum("none", "lane", "severity", "resource_type", "node")
- search_query: optional string
- time_window_start: optional string
- time_window_end: optional string

Purpose:
Projected UI filter state for rich trace viewers.

13. TRACE DIAGNOSTICS VIEW

TraceDiagnosticsView
- trace_complete: bool
- partial_reason: optional string
- load_warning_count: int
- load_error_count: int
- missing_event_ranges_present: bool
- missing_artifact_refs_present: bool
- last_error_label: optional string

Rules:
- incomplete trace must remain visibly incomplete
- missing data must not be hidden by aggregation

14. LIVE STREAM RULES

When source_mode = "live_event_stream":
- events may append over time
- timeline_status may remain streaming
- lane statuses may update incrementally
- relative ordering must reflect actual arrival/order metadata from engine

The viewer must not pretend the live stream is finalized.

15. HISTORICAL TRACE RULES

When source_mode = "execution_record_trace":
- the viewer is reading historical trace
- events are fixed history
- lane statuses reflect recorded outcomes
- the UI may optimize grouping, but must not rewrite event order/provenance

16. REPLAY TRACE RULES

When source_mode = "replay_trace":
- replay events must remain distinguishable from original execution events
- replay status is about the replay session, not the original run outcome
- original trace truth must remain intact

17. EVENT LINKAGE RULES

The viewer should support linking each event to related surfaces when available:

- graph node / edge / group
- inspector target
- validation finding
- execution panel status
- artifact viewer entry

Rules:
- links must be reference-safe
- missing linked objects must degrade gracefully

18. CONTEXT REFERENCE RULES

The viewer may expose context reads/writes as references.

Examples:
- input.question
- prompt.main.rendered
- provider.openai.output
- plugin.normalize.result
- output.final_answer

Rules:
- the viewer must not dump sensitive/full context by default
- refs must help inspect dependency flow without becoming raw storage mutation surfaces

19. LONG-RUN OBSERVABILITY RULES

The Trace / Timeline Viewer must remain useful for long-running executions.

It should support:
- progressive event arrival
- artifact preview linkage
- warnings/errors surfacing before completion
- retry visibility
- node/resource stage transitions

20. PANEL ACTION BOUNDARY

The Trace / Timeline Viewer may emit:
- focus-node actions
- focus-event actions
- open-artifact actions
- open-validation actions
- replay navigation actions

The Trace / Timeline Viewer must not:
- fabricate missing events
- reorder history as if it were truth
- mutate structural truth
- mutate execution record history
- collapse replay and original history into one ambiguous stream

21. MINIMUM FIRST IMPLEMENTATION

The first implementation of TraceTimelineViewerViewModel should support:

- source_mode
- timeline_status
- run identity
- summary counts
- basic lanes
- event list
- severity filtering
- focused slice
- replay availability state
- diagnostics for partial trace

22. FINAL DECISION

TraceTimelineViewerViewModel is the official UI-facing contract
for presenting temporal execution history, event streams,
timeline lanes, and replay-aware trace inspection in Nexa.

It is the stable history-and-temporal-observability projection layer
for Trace / Timeline Viewer UI modules.

It is not the trace source itself,
and it must never become a fabricated history layer.