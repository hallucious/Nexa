# Plugin Runtime Observability Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_runtime_observability_contract.md`

## 1. Purpose

This document defines the canonical runtime observability contract for plugins in Nexa.

It establishes:
- what plugin execution events must be observable
- how plugin runtime metrics are represented
- how plugin execution is linked to trace slices
- how context I/O, artifacts, failures, and recovery attempts become observable truth
- how runtime, UI, analytics, and governance layers consume one shared plugin observability model

## 2. Core Decision

1. Plugin runtime behavior must be observable as engine truth.
2. Observability must include events, metrics, and linkage, not just final status.
3. Plugin observability must remain compatible with Node as sole execution unit, Working Context I/O truth, artifact append-only truth, and failure/recovery truth.
4. UI may render observability, but must not fabricate it.
5. Observability must distinguish execution progress, context I/O facts, artifact creation, failures, recovery attempts, and final outcomes.

## 3. Non-Negotiable Boundaries

- Node boundary
- Context boundary
- Executor boundary
- Artifact boundary
- UI boundary

## 4. Core Vocabulary

- Plugin Runtime Event
- Plugin Metric
- Trace Slice
- Artifact Linkage
- Observability Stream
- Final Outcome Signal

## 5. Canonical Observability Lifecycle

PluginExecutionInstance
-> Runtime Event Emission
-> Metric Updates
-> Context I/O Linkage
-> Artifact Linkage
-> Failure / Recovery Linkage if any
-> Final Outcome Signal
-> Historical Trace Availability

## 6. Canonical Runtime Event Object

PluginRuntimeEvent
- event_id: string
- execution_instance_ref: string
- binding_ref: string
- node_execution_ref: string
- run_ref: string
- event_type: enum(
    "execution_queued",
    "execution_started",
    "input_extracted",
    "context_read_completed",
    "executor_invoked",
    "partial_output_emitted",
    "final_output_emitted",
    "artifact_emitted",
    "warning_emitted",
    "failure_detected",
    "recovery_attempted",
    "recovery_succeeded",
    "recovery_failed",
    "execution_completed",
    "execution_cancelled",
    "execution_timed_out"
  )
- timestamp: string
- severity: enum("info", "warning", "error", "critical")
- message: string | null
- related_context_keys: list[string]
- related_artifact_refs: list[string]
- related_failure_ref: string | null
- related_recovery_ref: string | null
- details: object | null

## 7. Canonical Metric Object

PluginRuntimeMetric
- metric_id: string
- execution_instance_ref: string
- binding_ref: string
- metric_name: string
- metric_type: enum("count", "duration_ms", "size_bytes", "token_count", "cost_estimate", "status", "custom")
- metric_value: string
- measured_at: string
- notes: string | null

## 8. Minimum Required Event Families

- lifecycle events
- context I/O events
- artifact events
- failure/recovery events
- warning/policy events

## 9. Minimum Required Metric Families

- duration
- volume
- size
- resource usage
- stability

## 10. Relationship to Context I/O and Failure / Recovery

Every meaningful context I/O stage should be observable either as an event, a metric, or both. Failures and recoveries must be linkable through related refs and terminal outcome signals.

## 11. Relationship to UI and Trace Viewers

UI modules such as trace/timeline, execution panel, artifact viewer, and diagnostics should consume this observability model, not invent incompatible state narratives.

## 12. Canonical Trace Slice Object

PluginTraceSlice
- trace_slice_id: string
- execution_instance_ref: string
- slice_type: enum(
    "full_execution",
    "input_phase",
    "executor_phase",
    "output_phase",
    "artifact_phase",
    "failure_phase",
    "recovery_phase"
  )
- started_at: string
- ended_at: string | null
- event_refs: list[string]
- metric_refs: list[string]
- outcome_summary: string | null

## 13. Final Outcome Signal

PluginExecutionOutcome
- outcome_id: string
- execution_instance_ref: string
- final_status: enum("completed", "failed", "cancelled", "timed_out", "partial_only")
- final_output_present: bool
- partial_output_present: bool
- artifact_present: bool
- failure_ref: string | null
- recovery_ref: string | null
- completed_at: string | null
- summary: string | null

## 14. Observability Stream Rules

- ordered
- linkable
- non-fabricated
- severity-aware
- terminally coherent

## 15. Explicitly Forbidden Patterns

- final-status-only observability
- UI-invented progress
- failure without observability
- artifact without linkage
- recovery invisibility
- context I/O opacity

## 16. Canonical Findings Categories

Examples:
- OBS_EXECUTION_STARTED
- OBS_INPUT_EXTRACTED
- OBS_CONTEXT_READ_COMPLETED
- OBS_EXECUTOR_INVOKED
- OBS_PARTIAL_OUTPUT_EMITTED
- OBS_FINAL_OUTPUT_EMITTED
- OBS_ARTIFACT_EMITTED
- OBS_FAILURE_DETECTED
- OBS_RECOVERY_ATTEMPTED
- OBS_EXECUTION_COMPLETED
- OBS_EXECUTION_TIMED_OUT

## 17. Relationship to Existing PRE / CORE / POST Stage Structure

This document does not replace the existing PRE / CORE / POST execution-stage vocabulary.

Interpretation rule:
- PRE / CORE / POST remains an execution-stage model
- this Observability contract defines how runtime facts emitted from that broader execution model become canonical observability truth
- coexistence remains mandatory unless an explicit migration document says otherwise

## 18. Relationship to Existing Plugin Contract v1.1.0

This document should be read as a cumulative refinement of the existing plugin direction centered on deterministic capability components, Working Context, PluginExecutor, and trace-aware execution.

## 19. Relationship to Current Codebase Alignment

This document defines the target observability model.
Current code may expose only part of this structure directly.

Implementation should therefore treat the model as partially aligned / migration-required where current event, metric, and trace linkage layers are thinner than the target contract.

## 20. Canonical Summary

- Plugin runtime behavior must be observable as engine truth.
- Observability includes events, metrics, trace slices, and artifact linkage.
- Working Context I/O, failure, recovery, and artifacts must all become inspectable through one shared model.
- UI may render it, but must not fabricate it.

## 21. Final Statement

A plugin in Nexa should not execute as a black box whose behavior is guessed afterward.

It should emit a truthful runtime observability stream that shows what happened, what changed, what failed, what recovered, and what evidence was produced.

That is the canonical meaning of Plugin Runtime Observability in Nexa.
