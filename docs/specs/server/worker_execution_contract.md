# Worker Execution Contract v1.1

## Recommended save path
`docs/specs/server/worker_execution_contract.md`

## 1. Purpose

This document defines the canonical async worker execution model for Phase 4.5.

Its purpose is to explain how accepted Nexa runs move through:

- queueing
- worker claim
- engine invocation
- status/result persistence
- terminal completion or failure handling

This document exists because the server contracts already use states such as `queued`, `running`, and `completed`, but the concrete worker lifecycle had not yet been defined.

This v1.1 update additionally fixes the worker-liveness gap by defining:

- claim lease behavior
- heartbeat expectations
- orphaned run detection and recovery

## 2. Core Decision

The async worker is a server-orchestration component, not a new execution semantics layer.

Official rule:

- the worker may claim queued runs
- the worker may invoke the engine through the official boundary
- the worker may persist product-facing projections of engine truth
- the worker may not redefine Node execution semantics, artifact truth, trace truth, or validation truth

In short:

The worker moves work through the system.
The engine still decides what the work means.

## 3. Position in the Overall Flow

Canonical flow:

Client
→ `POST /api/runs`
→ server auth / authorization / launch admission
→ run record created with queued status
→ execution job enqueued
→ worker claims queued job
→ worker invokes engine through the official boundary
→ engine emits canonical status/result/artifact/trace truth
→ worker persists product-facing projections
→ clients read status/result through server APIs

## 4. Worker Responsibility Boundary

The worker is allowed to:

- claim queued run jobs
- resolve run record / target / workspace context
- construct normalized engine launch/invocation input
- invoke the engine through the approved boundary
- persist run status/result/artifact/trace projections
- mark terminal worker-side infrastructure failures clearly

The worker is not allowed to:

- mutate circuit structure ad hoc
- invent fake progress
- reinterpret failed execution as success
- synthesize missing trace events
- overwrite append-only artifact meaning
- bypass the engine and fabricate terminal outcomes

## 5. Canonical Run Lifecycle

Recommended lifecycle:

### 5.1 `queued`
The server has admitted the run into product execution flow.

Meaning:
- product authorization passed
- run identity exists
- work has not yet begun in a worker

### 5.2 `starting`
A worker has claimed the run and is preparing engine invocation.

Meaning:
- worker claim succeeded
- execution target/context resolution is underway
- engine-side execution has not yet meaningfully progressed

### 5.3 `running`
Canonical execution is in progress.

Meaning:
- engine execution has started
- status/progress/events may now appear truthfully

### 5.4 terminal states
Recommended terminal families:
- `completed`
- `failed`
- `partial`
- `cancelled`

These must remain engine-compatible truths, not worker-invented labels.

## 6. Queue Claim Rule

Recommended rule:

- only one worker may hold the active claim for a run at a time
- claim/lease semantics should exist even if the implementation starts simply
- duplicate worker claims must not cause duplicate canonical execution

Meaning:
- queue duplication or retry races must be handled explicitly
- product convenience must not create double execution

## 7. Claim Lease and Heartbeat Rule

A worker claim must not be treated as permanent ownership.

Recommended rule:

- every claimed run has a lease window
- the active worker must refresh that lease through heartbeat updates while it still owns the run
- if lease refresh stops for too long, the claim becomes stale
- stale claims must be treated as orphan-risk signals, not as proof that execution is still healthy

Minimum recommended liveness fields:

- `claimed_by_worker_ref`
- `claimed_at`
- `lease_expires_at`
- `last_heartbeat_at`
- `worker_attempt_number`

Recommended interpretation:

- `claimed_at` tells when ownership began
- `last_heartbeat_at` tells the last confirmed liveness signal
- `lease_expires_at` defines when the claim becomes stale unless refreshed
- `worker_attempt_number` helps distinguish original claim from recovery attempts

Important:
- a lease/heartbeat system protects the run registry from permanently stale `running` claims
- heartbeat is worker/server liveness metadata, not engine execution meaning

## 8. Orphaned Run Detection and Recovery Rule

An orphaned run is a run whose worker claim has become stale without a terminal projection being written.

Recommended rule:

- if `lease_expires_at` passes without refresh and the run is still non-terminal, the run must be flagged for orphan review
- orphan review must distinguish:
  - worker crash / disappearance
  - delayed persistence update
  - genuine long-running engine execution still being supervised elsewhere
- recovery must be explicit and policy-bounded

Recommended recovery options:

1. mark as worker infrastructure failure if engine progress cannot be confirmed
2. requeue for a fresh worker attempt if policy allows safe retry
3. escalate to operator/manual inspection if duplication risk is too high
4. preserve current non-terminal state temporarily while bounded recovery checks run

Important:
- orphan recovery must never silently create duplicate canonical execution
- "not hearing from the worker" is not the same as "the engine definitely failed"
- orphan handling belongs to worker/server failure management, not engine semantics rewriting

## 9. Worker Bootstrap Inputs

The worker should receive or resolve at least:

- `run_id`
- workspace reference
- execution target reference
- requesting user reference where needed for audit context
- allowed runtime option context
- correlation/request metadata if available

The worker should not depend on:
- raw client UI state
- local `.nex.ui` continuity
- ad hoc hidden route-handler variables

## 10. Engine Invocation Rule

The worker must invoke the engine only through the approved engine boundary.

Recommended rule:

- worker builds normalized engine-facing request
- worker calls engine invocation adapter / `CircuitRunner` entry path through that adapter
- worker captures acceptance, status, result, failure, artifact, and trace outputs as canonical engine truth

This preserves:
- engine meaning
- product/server orchestration
- explicit boundary discipline

## 11. Status Update Rule

The worker may update product-facing run records as execution progresses.

Recommended projection sequence:

- queued
- starting
- running
- completed / failed / partial / cancelled

Important:
- these are product continuity projections of engine truth
- the worker must not report states that the engine has not actually reached
- `running` must not be published from optimism alone

Additional liveness rule:
- heartbeat metadata may update while the visible run status remains unchanged
- liveness refresh must not be mistaken for progress

## 12. Progress Rule

The worker may persist progress only when truthfully available.

Allowed progress families:
- no percent, only active node/event signal
- coarse node-level progress
- richer progress if the engine explicitly provides it

Forbidden:
- guessed percent values
- fake ETA presented as canonical truth

## 13. Result Persistence Rule

When the engine produces canonical terminal outcome data, the worker may persist:

- run record terminal status projection
- result envelope projection
- artifact refs / metadata
- trace refs / indexes / summaries
- cost/timing metrics when canonical values exist

The worker must not:
- flatten partial into success
- hide failed-but-meaningful result envelopes
- replace canonical artifacts with preview text

## 14. Failure Families

The worker contract must keep failure families separate.

### 14.1 Product-layer pre-worker rejection
Examples:
- unauthenticated
- forbidden
- quota blocked before enqueue
- invalid target not admitted into run flow

These happen before worker claim.

### 14.2 Worker infrastructure failure
Examples:
- queue claim failure
- worker crash
- dependency/bootstrap failure
- persistence write failure after claim
- lease expiry without recoverable liveness confirmation

These are worker/server failures.
They must be recorded as such and must not be mislabeled as canonical engine execution failure unless the engine actually failed.

### 14.3 Engine execution failure
Examples:
- validation blocked at engine start boundary
- provider/runtime failure
- canonical engine failed state
- engine partial result state

These remain engine-owned truths even though the worker transports them.

## 15. Retry Rule

Recommended initial rule:

- retries must be explicit and policy-bounded
- worker infrastructure retries and engine execution retries must not be conflated
- duplicate retries must not silently create multiple canonical runs unless the product policy explicitly permits that behavior

Meaning:
- route-handler retry, queue retry, and engine retry are different concepts
- they must stay distinguishable

Additional lease-related rule:
- orphan recovery retry must count as a new worker attempt
- retry metadata must preserve linkage to the original run identity

## 16. Cancellation Rule

Recommended rule:

- cancellation is a product/server request that must be propagated through the proper engine-aware control path
- the worker may reflect cancellation state changes
- the worker must not claim cancellation occurred if the engine has not actually confirmed a cancelled terminal state where such confirmation is required by the runtime model

## 17. Poll vs Push Rule

Recommended rule:

- polling through the status endpoint remains canonical
- push/subscription surfaces may later be added as secondary convenience channels
- worker updates must always be compatible with polling as the ground-truth client access path

This keeps the system robust even before real-time infrastructure is added.

## 18. Observability Rule

The worker should record enough metadata for diagnosis:

- when the job was claimed
- by which worker/worker class if appropriate
- when engine invocation began
- whether failure was worker-side or engine-side
- when terminal projection was written
- retry attempt count where applicable
- last heartbeat time
- lease expiry time when relevant
- orphan detection / recovery decisions when relevant

This is worker observability.
It does not replace canonical engine trace.

## 19. Relationship to Existing Contracts

This document depends on and must remain consistent with:

- Engine ↔ Server Layer Boundary Contract
- Run Launch API Contract
- Run Status API Contract
- Run Result API Contract
- Run Record Persistence Contract

If there is conflict, engine-owned truth semantics override worker convenience.

## 20. What Must Never Happen

The following are forbidden:

1. worker inventing engine success without canonical engine completion
2. duplicate worker claims producing duplicate canonical execution accidentally
3. worker-side bootstrap failure being misreported as canonical engine failure
4. fake progress/ETA being written as product truth
5. local UI continuity influencing canonical server execution state
6. worker mutating append-only artifact meaning
7. trace synthesis by worker code
8. stale worker claims being left indefinitely as if they prove healthy execution
9. orphan recovery creating silent duplicate execution

## 21. Final Statement

The Nexa worker is an orchestration layer for queued product execution.

It is not a second runtime.
It is not a second truth system.

Its job is to move admitted runs through the official engine boundary, maintain trustworthy liveness tracking, and persist trustworthy product projections of what the engine actually did.
