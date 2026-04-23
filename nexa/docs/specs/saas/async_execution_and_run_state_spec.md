# Nexa Async Execution and Run State Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Runtime specification
Authority scope: Queue-backed execution, run submission, run state, and recovery semantics
Recommended path: `docs/specs/saas/async_execution_and_run_state_spec.md`

## 1. Purpose

This document defines how the Nexa SaaS handles run submission and run execution once the product moves beyond the synchronous P0 seam.

Its purpose is to fix:
- why the SaaS must use asynchronous execution,
- what data exists before and after queue submission,
- which state system is authoritative at each phase,
- how recovery works when Redis is lost,
- what admin reprocessing is allowed to do,
- and what a valid run lifecycle looks like.

## 2. Problem statement

Synchronous browser-facing execution is not acceptable for the first real SaaS product.

The first target use case includes long-running contract review jobs.
Therefore:
- the HTTP request must return quickly,
- execution must continue in the background,
- and product state must show the run lifecycle without relying on an open browser connection.

## 3. Runtime architecture

### 3.1 Queue backend

The SaaS runtime uses:
- Redis for queue transport,
- arq as the queue runtime,
- worker processes for background execution,
- Postgres as authoritative business-state storage.

### 3.2 Core principle

Redis is not the source of durable business truth.
Redis is the execution transport and transient queue state.
Durable truth must live in Postgres.

## 4. Run submission lifecycle

### 4.1 Submission sequence

A valid run submission follows this order:

1. request is authenticated and authorized,
2. quota/preflight checks pass,
3. any file references are already in a usable state,
4. a `run_submissions` row is inserted into Postgres,
5. only then is the job enqueued to Redis,
6. the API returns immediately with queued/submitted status.

This order is mandatory.
If the queue is written before the durable submission record exists, Redis-loss recovery becomes unsafe.

### 4.2 Why `run_submissions` exists

`run_submissions` exists to bridge the gap between:
- user intent,
- transient queue state,
- and durable execution outcomes.

It is the authoritative durable record that a run was accepted for processing even if Redis is later lost.

## 5. Run state surfaces

There are at least three related but non-identical state surfaces:

1. **Submission state** — whether the product accepted the run request
2. **Queue state** — whether the job is queued, claimed, retried, or orphaned
3. **Execution result state** — whether execution ultimately completed, failed, or produced a stored result

A valid implementation must keep these surfaces distinguishable.

## 6. `run_submissions` semantics

### 6.1 Table role

`run_submissions` is a short-lived operational truth table.
It stores:
- run identity,
- submitter reference,
- target reference,
- provider/model choice,
- submission timestamp,
- and a bounded submission status.

### 6.2 Category

`run_submissions` is Category C:
- TTL-bounded,
- cleanup-job deletable,
- but operationally mutable while still active.

### 6.3 Allowed status progression

Typical status progression:

- `submitted`
- `queued`
- `requeued`
- `completed`
- `failed`
- `lost_redis`

The exact set may expand later, but the product must preserve the distinction between:
- accepted but not yet run,
- running/queued,
- terminal success/failure,
- and unrecoverable queue transport loss.

## 7. Worker execution behavior

### 7.1 Worker responsibility

The worker is responsible for:
- claiming queue work,
- invoking the engine through approved boundaries,
- writing execution results to durable storage,
- and emitting lifecycle transitions/events.

### 7.2 Worker must not become business-state authority

The worker may compute.
It may not redefine authoritative business state outside the durable stores.

### 7.3 Auto-recovery

Provider fallback and retry logic may exist in worker error handling, but:
- it must be governed by explicit policy,
- it must be auditable,
- and it must not erase the original failure history.

## 8. Relationship between Redis and Postgres

### 8.1 Redis role

Redis stores:
- queued jobs,
- transient worker claim state,
- result cache or temporary queue-related data.

### 8.2 Postgres role

Postgres stores:
- submitted run intent,
- execution record truth,
- supporting lifecycle logs,
- and other durable operational state.

### 8.3 Recovery rule

If Redis and Postgres disagree, Postgres is authoritative for:
- whether the run was accepted,
- whether the run completed,
- and whether a durable result exists.

## 9. Redis loss recovery

### 9.1 Recovery objective

Redis loss must not destroy the product’s knowledge that a run was accepted.

### 9.2 Recovery logic

Recovery must compare:
- `run_submissions`
- against terminal execution records

and determine which accepted runs did not finish.

### 9.3 Re-enqueue rule

If a previously accepted run is still recoverable according to policy and time window, it may be re-enqueued through an admin-approved or explicitly defined recovery path.

### 9.4 Non-recoverable submissions

If the recovery window has passed, the system may mark the submission as lost and require resubmission.
This must be communicated as an explicit state, not a silent disappearance.

## 10. Run result truth

### 10.1 Authoritative completed state

A run is not truly complete because Redis says so.
A run is complete when the durable execution result has been written according to the execution record rules.

### 10.2 Result retrieval

The API-facing result and trace retrieval surfaces are downstream of durable execution records and related view layers.
They must not depend on Redis cache for correctness.

## 11. Action surfaces for admin/support

Admin/support actions such as:
- retry,
- force-reset,
- reprocess-orphans,
- and diagnosis

must operate through controlled service surfaces, not by bypassing the queue and directly mutating hidden state.

Every such action must remain auditable.

## 12. Observability requirements for execution state

A valid runtime should expose enough observability to answer:
- what was submitted,
- what is queued,
- what is running,
- what failed,
- what retried,
- what is orphaned,
- and what actually completed.

This observability must avoid document-content leakage and follow the redaction specification.

## 13. Non-goals

This document does not define:
- token streaming,
- conversational incremental execution,
- advanced batch execution,
- broad autonomous retry policy,
- or user-facing workflow editing.

## 14. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. HTTP run submission becomes non-blocking,
2. durable submission state exists before queue submission,
3. Redis loss does not erase accepted-run knowledge,
4. completed execution truth is durable and queryable,
5. queue state and result state remain distinguishable,
6. retry/recovery flows are explicit and auditable,
7. and admin actions do not bypass runtime governance.
