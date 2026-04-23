# Execution Streaming Contract

## Recommended save path
`docs/specs/execution/execution_streaming_contract.md`

## 1. Purpose

This document defines the canonical execution-streaming contract for Nexa when engine-level contract changes are allowed.

Its purpose is to make long-running circuit execution observable in real time without violating Nexa core invariants.

This contract exists because user-facing runtime value is not only:
- final completion
but also:
- visible progress
- incremental result emergence
- current execution focus
- meaningful waiting-state feedback
- traceable partial output flow

Execution streaming must therefore become an explicit engine contract,
not an accidental UI-side convenience layer.

## 2. Core Decision

Execution streaming must be treated as a first-class execution contract.

Official rule:

- streaming is an engine-originated runtime capability
- UI may render streaming, but must not fabricate it
- streaming must remain compatible with execution truth, artifact truth, and trace truth
- partial output must remain distinguishable from final output
- streaming must not redefine Node as the sole execution unit

In short:

Nexa execution streaming is a truthful incremental projection of execution,
not a UI illusion.

## 3. Non-Negotiable Boundaries

The following must remain unchanged:

- Node remains the sole execution unit
- dependency-based execution remains the runtime rule
- engine-owned execution truth remains authoritative
- artifact append-only principles remain intact
- trace/history truth remains engine-owned
- storage truth is not redefined by streaming
- UI does not invent progress or output tokens that the engine did not emit

This contract may extend provider/runtime behavior,
but it must not turn Nexa into a fake-progress system.

## 4. Streaming Lifecycle

Canonical lifecycle:

Execution Started
-> Node Started
-> Resource Streaming Started
-> Stream Chunk Events
-> Partial Output Projection
-> Stream Completion
-> Node Output Finalization
-> Execution Completion / Failure

Every streamed run must preserve this lifecycle explicitly,
even if some nodes do not stream and only emit final output.

## 5. Contract Family Overview

This contract family contains five conceptual layers:

1. Provider Streaming Contract
2. Node Streaming Contract
3. Stream Event Contract
4. Partial Output Contract
5. Streaming Trace / Record Contract

## 6. Provider Streaming Contract

### 6.1 Purpose
A provider streaming contract defines how a provider emits incremental response units instead of only a final response envelope.

### 6.2 Canonical provider capability model

ProviderStreamingCapability
- provider_ref: string
- supports_streaming: bool
- stream_mode: enum("token", "chunk", "message_part", "none")
- partial_usage_reporting: bool
- partial_finish_signal: bool
- supports_cancel: bool
- supports_pause: bool

### 6.3 Rules
- a provider may support final-only execution
- if streaming is supported, the mode must be declared explicitly
- provider streaming must not bypass normal provider resolution or runtime policy
- a provider stream must be cancellable if the provider contract claims cancel support

## 7. Node Streaming Contract

### 7.1 Purpose
Node streaming defines how a node exposes incremental execution state while still remaining one bounded execution unit.

### 7.2 Canonical node streaming object

NodeStreamingState
- node_ref: string
- streaming_status: enum(
    "not_streaming",
    "streaming_pending",
    "streaming_active",
    "streaming_paused",
    "streaming_completed",
    "streaming_failed"
  )
- active_resource_ref: optional string
- chunk_count: int
- partial_output_ref: optional string
- latest_chunk_time: optional string
- can_cancel: bool
- can_pause: bool

### 7.3 Rules
- node streaming state must remain node-scoped
- resource-level streaming may occur inside the node, but the node remains the runtime execution unit
- node completion must remain separate from stream-chunk arrival
- a node may stream and still ultimately fail

## 8. Stream Event Contract

### 8.1 Purpose
Stream events define the canonical event language used to surface incremental execution truth.

### 8.2 Canonical stream event object

ExecutionStreamEvent
- event_id: string
- run_ref: string
- node_ref: string
- resource_ref: optional string
- event_type: enum(
    "stream_opened",
    "stream_chunk",
    "stream_progress",
    "partial_output_updated",
    "stream_paused",
    "stream_resumed",
    "stream_completed",
    "stream_failed",
    "stream_cancelled"
  )
- timestamp: string
- payload: object
- sequence_no: int

### 8.3 Rules
- sequence ordering must be explicit
- stream events must be distinguishable from non-stream execution events
- partial-output updates must not be mislabeled as final output
- failure and cancellation must be represented explicitly

## 9. Partial Output Contract

### 9.1 Purpose
Partial output defines what can be shown to users while execution is still in progress.

### 9.2 Canonical partial output object

PartialOutputProjection
- projection_id: string
- node_ref: string
- output_kind: enum("text", "structured_partial", "summary", "unknown")
- content_preview: optional object
- is_final: bool
- confidence: enum("low", "tentative", "final")
- update_count: int
- last_updated_at: optional string

### 9.3 Rules
- partial output must always be visibly marked as non-final until finalization
- partial output must be replaceable or extendable by later chunks
- final output resolution remains an execution/runtime decision, not a UI assumption
- partial output must not overwrite finalized output truth

## 10. Streaming Trace / Record Contract

### 10.1 Purpose
Streaming activity must remain inspectable in trace/history without collapsing incremental events into a misleading single result.

### 10.2 Canonical streaming record object

StreamingExecutionRecord
- run_ref: string
- node_ref: string
- stream_supported: bool
- stream_used: bool
- stream_mode: optional string
- chunk_count: int
- first_chunk_at: optional string
- last_chunk_at: optional string
- stream_terminal_status: enum(
    "completed",
    "failed",
    "cancelled",
    "not_used",
    "unknown"
  )
- final_output_ref: optional string
- partial_output_refs: list[string]
- diagnostics: optional list[object]

### 10.3 Rules
- streaming trace must remain linked to the main execution record
- partial and final outputs must remain distinguishable
- a stream may terminate before a successful final output exists
- replay/debug tooling must preserve the difference between streamed progression and finalized result

## 11. Waiting-State and Progress Semantics

### 11.1 Purpose
Streaming is not only about output chunks.
It is also about making waiting states legible.

### 11.2 Minimum engine-visible states
The engine should make the following states available when possible:

- current active node
- current active resource
- whether output is streaming or only waiting
- whether progress is known or unknown
- whether output has started appearing
- whether the stream is stalled, paused, failed, or complete

### 11.3 Rule
Unknown progress must remain explicitly unknown.
The engine must not fabricate percentage completion just to satisfy UI expectations.

## 12. Cancellation and Pause Boundary

### 12.1 Cancellation
If streaming execution is cancelled:
- the cancellation must be explicit in event and trace records
- partial output may remain inspectable
- cancellation must not be misreported as successful completion

### 12.2 Pause
If pause is supported:
- pause capability must be declared by the provider/runtime path
- pause/resume events must be recordable
- pause must not imply persistence guarantees unless checkpointing is separately supported

## 13. UX and Visibility Requirements

Even though this is an engine-facing contract, it must support user-facing visibility.

Minimum UX-visible facts:
- which node is currently active
- whether the system is waiting or streaming
- whether visible output is partial or final
- whether execution can be cancelled
- whether the stream failed, stalled, paused, or completed

This contract must support future beginner-safe runtime surfaces without requiring redefinition of engine truth.

## 14. Relationship to Other Contracts

This contract is compatible with, but distinct from:

- Automation Trigger / Delivery Contract
- Execution Panel runtime projection
- Trace / Timeline Viewer
- Artifact Viewer
- quota and safety boundaries
- future checkpoint/replay contracts

Execution streaming should integrate with those contracts,
but it must remain independently valid as an execution-layer contract.

## 15. Initial Prioritization Guidance

For general-user engine expansion, this contract belongs to Stage 1 engine-facing value work.

Recommended implementation direction:

1. define provider streaming capability first
2. define node-scoped stream state second
3. define canonical stream events third
4. define partial output projection fourth
5. link streaming records into trace/history without collapsing them into fake final output
6. keep streaming compatible with quota, safety, and cancellation from the start

## 16. Explicit Non-Goals

This v1 contract does not define:

- conversational follow-up execution
- cross-run memory semantics
- batch execution semantics
- checkpoint persistence guarantees
- arbitrary looped streaming orchestration
- UI rendering implementation details

Those belong to later contracts or later architectural phases.

## 17. Final Statement

Execution streaming in Nexa must be a truthful incremental execution contract.

The engine must not reduce streaming to a UI trick,
and UI must not pretend that partial output is final output.

For general-user trust, streaming must expose progress honestly,
output incrementally,
and preserve the difference between partial emergence and finalized execution truth.