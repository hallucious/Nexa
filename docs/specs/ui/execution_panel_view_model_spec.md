[DESIGN]
[EXECUTION_PANEL_VIEW_MODEL_SPEC v0.1]

1. PURPOSE

This document defines the official Execution Panel View Model
for Nexa UI.

Its purpose is to provide a stable, UI-friendly representation of:

- execution status
- current run state
- progress
- latest events
- latest outputs
- execution controls
- run-scoped warnings and errors

The Execution Panel is the primary runtime-status-and-control module
of the Nexa UI shell.

It is responsible for:

- showing whether the current target is idle, queued, running, completed, failed, partial, or cancelled
- showing current progress and active node context
- exposing recent execution events
- showing latest output summaries
- showing run-level timing and metrics
- exposing bounded control actions such as run / cancel / pause / resume / replay when allowed

It is not responsible for inventing execution truth,
fabricating trace/history,
or directly mutating structural truth.

2. POSITION IN UI ARCHITECTURE

The Execution Panel consumes data only through the adapter/view-model boundary.

Flow:

Engine truth
→ UI Adapter / View Model Layer
→ ExecutionPanelViewModel
→ Execution Panel UI Module

The Execution Panel must never directly read or mutate raw engine internals.

3. CORE PRINCIPLES

3.1 Execution Panel is a run-state projection layer, not a truth layer.
3.2 Execution truth remains engine-owned.
3.3 Execution Panel may show controls, but control availability is engine-gated.
3.4 Execution status must come from engine evidence, not UI reconstruction.
3.5 Partial, failed, and cancelled runs must remain visible as first-class states.
3.6 Long-running execution must remain observable.
3.7 Run history and live execution must be distinguishable.

4. TOP-LEVEL VIEW MODEL

ExecutionPanelViewModel
- source_mode: enum(
    "live_execution",
    "execution_record",
    "replay_session",
    "designer_test_run",
    "unknown"
  )
- storage_role: enum("working_save", "commit_snapshot", "execution_record", "none")
- execution_status: enum(
    "idle",
    "queued",
    "running",
    "completed",
    "failed",
    "partial",
    "cancelled",
    "unknown"
  )
- run_identity: RunIdentityView
- progress: ExecutionProgressView
- active_context: ActiveExecutionContextView
- recent_events: list[ExecutionEventView]
- latest_outputs: list[OutputSummaryView]
- diagnostics: ExecutionDiagnosticsSummary
- timing: ExecutionTimingView
- metrics: ExecutionMetricsView
- control_state: ExecutionControlStateView
- related_findings: list[ExecutionFindingRefView]
- explanation: optional string

5. FIELD SEMANTICS

5.1 source_mode
Indicates what kind of execution surface is being shown.

Examples:
- live_execution
- execution_record
- replay_session
- designer_test_run

The UI must not infer this only from status.

5.2 storage_role
Indicates which storage layer the panel is currently anchored to.

5.3 execution_status
Top-level current execution state.

Semantics:
- idle: no active run
- queued: accepted but not yet running
- running: actively executing
- completed: run ended successfully
- failed: run ended in failure
- partial: run ended with partial result / partial completion
- cancelled: run ended due to cancellation
- unknown: insufficient data to determine safely

5.4 run_identity
Stable identifiers and source references for the current run.

5.5 progress
Structured progress projection.

5.6 active_context
Current node/stage/resource context if available.

5.7 recent_events
Most recent execution events in UI-friendly form.

5.8 latest_outputs
Compact summaries of current or final outputs.

5.9 diagnostics
Run-level warning/error summary.

5.10 timing / metrics
Timing and metric summaries suitable for runtime inspection.

5.11 control_state
Allowed/disabled control actions and reasons.

6. RUN IDENTITY VIEW

RunIdentityView
- run_id: optional string
- execution_id: optional string
- commit_id: optional string
- working_save_id: optional string
- trigger_type: optional enum(
    "manual_run",
    "designer_test_run",
    "replay_run",
    "system_run",
    "benchmark_run",
    "unknown"
  )
- title: optional string
- description: optional string

Rules:
- execution identity must come from engine/run artifacts
- UI must not fabricate run_id
- commit_id may be absent for purely local/live draft testing if engine permits that later

7. EXECUTION PROGRESS VIEW

ExecutionProgressView
- progress_mode: enum(
    "indeterminate",
    "node_count",
    "work_units",
    "percent_only",
    "unknown"
  )
- percent: optional float
- completed_units: optional int
- total_units: optional int
- current_stage_label: optional string
- eta_seconds: optional float
- indeterminate_message: optional string

Rules:
- percent must only be shown when engine can support it
- indeterminate progress must remain explicit
- ETA must not be presented as precise truth if it is heuristic

8. ACTIVE EXECUTION CONTEXT VIEW

ActiveExecutionContextView
- active_node_id: optional string
- active_node_label: optional string
- active_resource_type: optional enum(
    "prompt",
    "provider",
    "plugin",
    "subcircuit",
    "runtime",
    "unknown"
  )
- active_resource_id: optional string
- active_stage: optional string
- status_message: optional string

Purpose:
Shows what is happening right now.

Examples:
- rendering prompt
- executing provider
- waiting for plugin result
- replaying execution record
- finalizing outputs

9. EXECUTION EVENT VIEW

ExecutionEventView
- event_id: string
- event_type: string
- timestamp: string
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
- severity: optional enum("info", "warning", "error")
- short_message: string
- details_preview: optional string
- location_ref: optional string

Rules:
- events are UI-friendly projections of engine events
- event_type must not imply unrecorded truth
- location_ref should map to node/resource when possible

10. OUTPUT SUMMARY VIEW

OutputSummaryView
- output_name: string
- value_preview: string
- output_type: optional string
- source_ref: optional string
- is_partial: bool
- is_final: bool

Purpose:
Shows concise output summaries without requiring full artifact expansion.

Rules:
- partial outputs must remain distinguishable
- preview text must not pretend to be the entire artifact unless it is

11. EXECUTION DIAGNOSTICS SUMMARY

ExecutionDiagnosticsSummary
- warning_count: int
- error_count: int
- failure_reason_code: optional string
- failure_label: optional string
- partial_result_present: bool
- retry_count: optional int
- last_warning_label: optional string

Purpose:
Compact run-level health summary.

12. EXECUTION TIMING VIEW

ExecutionTimingView
- created_at: optional string
- started_at: optional string
- finished_at: optional string
- elapsed_seconds: optional float
- queue_wait_seconds: optional float

Rules:
- elapsed_seconds should come from engine timing when available
- finished_at must remain absent for active live runs

13. EXECUTION METRICS VIEW

ExecutionMetricsView
- processed_node_count: optional int
- total_node_count: optional int
- completed_node_count: optional int
- failed_node_count: optional int
- running_node_count: optional int
- emitted_event_count: optional int
- artifact_count: optional int

Purpose:
Compact runtime metrics for status and observability.

14. EXECUTION CONTROL STATE VIEW

ExecutionControlStateView
- can_run: bool
- can_cancel: bool
- can_pause: bool
- can_resume: bool
- can_replay: bool
- run_reason_disabled: optional string
- cancel_reason_disabled: optional string
- pause_reason_disabled: optional string
- resume_reason_disabled: optional string
- replay_reason_disabled: optional string

Rules:
- control enablement must be engine-gated
- UI must not present unavailable controls as available
- replay availability must depend on actual execution-record/replay support

15. EXECUTION FINDING REFERENCE VIEW

ExecutionFindingRefView
- finding_id: string
- severity: enum("info", "warning", "error", "blocked")
- short_label: string
- source_type: enum("execution", "validation", "replay", "unknown")
- location_ref: optional string

Purpose:
Allows Execution Panel to reference related validation/execution concerns.

16. LIVE VS HISTORICAL RULES

16.1 Live execution
When source_mode = "live_execution":
- status may change over time
- progress may update
- controls may be enabled
- recent_events should prefer newest items

16.2 Execution record
When source_mode = "execution_record":
- data is historical
- structural controls must be disabled
- replay may be available if supported
- timing and outputs should reflect recorded truth

16.3 Replay session
When source_mode = "replay_session":
- status reflects replay state, not original live execution state
- the UI must distinguish replay from original run

17. PARTIAL / FAILED / CANCELLED VISIBILITY RULES

The panel must not collapse these states into generic “not completed”.

17.1 failed
Hard failure with reason and relevant diagnostics.

17.2 partial
Ended with incomplete but meaningful outputs.

17.3 cancelled
Stopped by user/system cancellation.

Rule:
These states are semantically different and must remain distinct.

18. LONG-RUN OBSERVABILITY RULES

The Execution Panel must support long-running work.

It should remain usable when:
- percent is unavailable
- only node-level progress is known
- only event-stream progress is known
- outputs arrive incrementally
- warnings appear before completion

This aligns with Nexa’s observability direction for event streams and intermediate visibility.

19. STORAGE ROLE RULES

19.1 working_save
- may expose run controls for current draft context when engine allows
- may show latest execution summary for the editable artifact

19.2 commit_snapshot
- may serve as the structural anchor for a new run
- run controls may be enabled depending on engine policy

19.3 execution_record
- primarily readonly history surface
- structural mutation controls must remain disabled
- replay may be enabled when supported

20. EXECUTION PANEL ACTION BOUNDARY

The Execution Panel may emit:
- run requests
- cancel requests
- pause requests
- resume requests
- replay requests
- focus-node / focus-event navigation hints

The Execution Panel must not:
- fabricate execution status
- invent trace/history
- directly alter structural truth
- silently convert failed runs into successful-looking UI states
- bypass engine execution gating

21. MINIMUM FIRST IMPLEMENTATION

The first implementation of ExecutionPanelViewModel should support:

- execution_status
- run_identity
- progress
- active_context
- recent_events
- latest_outputs
- diagnostics summary
- timing summary
- control-state gating
- live_execution and execution_record modes

22. FINAL DECISION

ExecutionPanelViewModel is the official UI-facing contract
for presenting execution truth, runtime status, progress,
events, outputs, and bounded run controls in Nexa.

It is the stable runtime-status-and-control projection layer
for Execution Panel UI modules.

It is not the runtime itself,
and it must never become a source of fabricated execution truth.