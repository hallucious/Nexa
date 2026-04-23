# Authenticated Persistent Execution Slice

Spec version: 1.0
Status: Approved
Document type: Specification
Authority scope: Authenticated persistent execution slice only
Supersedes: None
Owner: 재선
Approval date: 2026-04-22
Recommended path: docs/specs/server/authenticated_persistent_execution_slice.md

## 1. Purpose

This document defines the specification for Nexa's authenticated persistent execution slice.

Its purpose is to fix the required behavior of the smallest server-side slice that proves all of the following together:

- authenticated HTTP access
- persistent server-side state
- executable run submission
- deterministic engine invocation through the server boundary
- retrievable result and trace outputs
- readiness signaling that reflects actual execution availability

This document is a specification of the feature behavior.
It is not an implementation directive.
It does not replace constitutional documents or implementation briefs.

## 2. Scope

This specification covers the server-side slice in which an authenticated client can:

- create and read workspaces
- submit an execution request
- poll run state
- read the final result envelope
- read execution trace data
- observe liveness and readiness state

This specification also covers the minimum persistence and execution-safety rules required for that slice to be trustworthy.

This specification does not cover:

- frontend UI behavior
- mobile packaging
- async worker queues
- public sharing flows
- billing flows
- streaming execution output
- external delivery destinations
- trigger automation

## 3. Relationship to Nexa core rules

A conforming implementation of this specification must preserve the following Nexa rules:

- Node remains the only execution unit.
- Circuit defines topology only and does not execute.
- Execution remains dependency-driven.
- Committed execution records remain append-only.
- Deterministic execution remains required under identical inputs and configuration.
- Plugin isolation remains unchanged.
- Contract-driven architecture remains in force.
- Server-to-engine access must cross the engine public boundary only.

This specification also depends on the following operational rule:

Storage-role truth must remain intact.
`working_save` and `commit_snapshot` are distinct storage roles.
Public HTTP execution in this slice must target `commit_snapshot` only.
Any `working_save` execution path is non-public and must remain explicitly gated.

## 4. Functional surface

A conforming implementation must expose a minimum authenticated API surface that supports the following capabilities:

1. Liveness check
2. Readiness check
3. Workspace list
4. Workspace creation
5. Workspace detail
6. Run submission
7. Run status polling
8. Run result retrieval
9. Run trace retrieval

The exact route shape may follow the currently approved server API, but the behavioral surface must contain these capabilities.

## 5. Authentication behavior

### 5.1 Required behavior

The slice must require authenticated access for user-scoped server operations.
Authentication must validate a signed token and derive a verified claims bundle before identity normalization.

### 5.2 Boundary rule

Identity-provider-specific logic must stop at the claims-verification layer.
Below verified claims, request auth context and authorization logic must remain provider-agnostic.

### 5.3 Dev and staging rule

A development stub mode may exist for local development and CI.
It must not be active in production.
It must not be active on any externally reachable staging environment.

## 6. Persistent state requirements

A conforming implementation must persist at least the following categories of server state:

- workspace state
- membership or user-to-workspace linkage
- provider binding state
- execution record state
- idempotency dedupe state

Persistence must survive process restart.
An in-memory-only implementation does not satisfy this specification.

## 7. Execution submission behavior

### 7.1 Execution path

Run submission must cross the server boundary into the engine through the approved engine public boundary only.
The server must not directly depend on circuit internals or engine validation internals.

### 7.2 Execution mode

The slice may use synchronous engine execution, but a server implementation must not block the async request loop directly.
If synchronous execution is used under async HTTP handling, it must be offloaded through a bounded threadpool or an equivalent non-blocking boundary.

### 7.3 Storage-role policy

Public HTTP execution must reject targets whose resolved storage role is not permitted for the slice.
By default, the permitted public execution target is `commit_snapshot` only.
A rejected target must fail with a stable, machine-readable reason.

### 7.4 Deterministic target resolution

Execution target resolution must be typed and canonical.
The same workspace reference and target reference must resolve to the same effective execution target shape under identical state.
A raw untyped dictionary loader is not sufficient as the normative contract surface.

## 8. Idempotency behavior

### 8.1 Submission deduplication

Run submission must support an optional idempotency key.
When the same workspace and the same idempotency key are submitted again within the valid dedupe window, the server must return the existing run identity and must not invoke the engine again.

### 8.2 Required relation to run duration

The configured idempotency window must be greater than the configured maximum run duration.
A conforming implementation must reject startup if this relation is violated.
This is a configuration safety rule, not a best-effort warning.

### 8.3 Guard behavior

The startup guard enforcing this relation must use an explicit runtime exception path.
It must not rely on Python `assert` semantics.

## 9. Execution record behavior

### 9.1 Append-only rule

Committed execution records must be append-only.
A conforming implementation must not update committed execution records in place.
If a later run supersedes an earlier run, that relationship must be expressed as forward-link information on the newer record or an equivalent append-only structure.

### 9.2 Result and trace retrieval

A completed run must expose:

- a result envelope suitable for API retrieval
- a trace representation suitable for API retrieval

The trace must contain at least one meaningful execution event for a successful non-empty run.

## 10. Readiness and liveness behavior

### 10.1 Liveness

The liveness endpoint must answer whether the process is alive.
It must not require engine execution or deep dependency checks.

### 10.2 Readiness

The readiness endpoint must answer whether the slice is actually ready to accept and complete an execution request.
It must reflect at least the following:

- database connectivity
- migration head status
- provider readiness
- provider mode

### 10.3 Provider mode visibility

The readiness payload must distinguish between at least these readiness modes:

- `dev_stub`
- `real`

This distinction is required so that external observers do not confuse development-only execution readiness with production-grade provider readiness.

## 11. Surface profile behavior

A constrained surface mode may hide non-slice routes from public exposure.
If such a profile exists, it must be understood as route exposure control only.
It must not be misrepresented as full dependency minimization or full subsystem removal.
The full internal router may still exist beneath the exposure filter.

## 12. Import-boundary behavior

A conforming implementation must preserve the server and engine boundary as follows:

- engine code must not import server code
- server code may cross into the engine through the approved engine public boundary only
- server code must not import circuit internals directly
- server code must not import engine validation internals directly

This boundary should be mechanically testable.

## 13. Non-goals

This specification does not require:

- replacement of the existing auth provider
- self-hosted authentication
- queue-backed execution
- streaming partial output
- worker orchestration
- UI rendering
- refactoring legacy files unrelated to this slice
- broad cleanup outside the required server-side slice

## 14. Acceptance criteria

A conforming implementation satisfies this specification only if all of the following are true:

1. The authenticated server slice is reachable through HTTP.
2. Persistent state is backed by a real database.
3. A workspace can be created and read.
4. A run can be submitted through HTTP.
5. Submission reaches real engine execution through the approved boundary.
6. Public execution enforces storage-role truth.
7. Duplicate submission within the valid window does not invoke the engine twice.
8. Result retrieval succeeds.
9. Trace retrieval succeeds.
10. Liveness and readiness endpoints report the expected state categories.
11. Committed execution records remain append-only.
12. Import-boundary contract tests remain green.
13. Existing baseline tests do not regress.

## 15. Relationship to implementation material

This document defines the behavior that the implementation must satisfy.
Implementation-specific file edits, creation order, exact scaffolding, and code-level execution sequence may be governed by a separate implementation brief.

If an implementation brief conflicts with this specification on feature behavior, this specification is authoritative for the behavior of the slice.
