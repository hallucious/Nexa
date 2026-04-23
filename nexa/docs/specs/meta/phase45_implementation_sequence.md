# Phase 4.5 Implementation Sequence v1

## Recommended save path
`docs/specs/meta/phase45_implementation_sequence.md`

## 1. Purpose

This document defines the recommended implementation order for Phase 4.5 in Nexa.

Its purpose is to convert the now-stabilized Phase 4.5 design set into a practical coding sequence that:

- minimizes rework
- preserves engine/server separation
- avoids premature coupling
- respects the approved infrastructure direction
- allows progressive validation during implementation

This document is not a product roadmap for users.
It is an implementation-order document for development work.

## 2. Preconditions

This sequence assumes the following document set is already accepted:

- Phase 4.5 implementation gate checklist
- six infrastructure decision records
- Phase 4.5 architecture summary
- Engine ↔ Server boundary contract
- run/status/result server contracts
- artifact/trace/run-record contracts
- auth adapter contract
- DB append-only / lineage contract
- engine boundary type mapping
- worker execution contract
- Phase 4.5 document set index

If these are not accepted, this sequence should not be treated as stable.

## 3. Core Implementation Principle

The correct order is:

1. establish translation boundaries first
2. establish persistence and identity foundations second
3. establish run admission and orchestration third
4. establish read/query surfaces fourth
5. establish product continuity and refinement fifth

In short:

Do not start from UI endpoints or convenience routes.
Start from the narrowest stable engine/server seam and build outward.

## 4. Recommended Implementation Order

### Stage 1 — Engine/Server Adapter Foundation

#### Goal
Create the explicit adapter layer that prevents ad hoc coupling between server contracts and engine internals.

#### Why first
Without this stage, every later server/API implementation risks hardcoding assumptions about current engine classes in random places.

#### Scope
Implement thin adapter boundaries for:

- `EngineLaunchAdapter`
- `ExecutionRecordResultAdapter`
- `ValidationFindingAdapter`
- `TraceEventAdapter`
- `ArtifactReferenceAdapter`
- `EngineStatusProjectionAdapter`

#### Required source alignment
This stage must use:
- `engine_server_boundary_contract.md`
- `engine_boundary_type_mapping.md`

#### Deliverables
- server-to-engine adapter module(s)
- typed boundary-object constructors or mappers
- proof that engine-facing types are not leaking directly into route handlers

#### Done criteria
- no route handler or worker directly hand-builds engine DTOs ad hoc
- one official mapping path exists for each major boundary object family
- Clerk-specific types are still absent from engine-core code

---

### Stage 2 — Auth Adapter and Server Identity Foundation

#### Goal
Establish authentication isolation before real server endpoints spread.

#### Why second
If auth is allowed to leak first, it will spread into route handlers, DB logic, and worker logic before the abstraction is stable.

#### Scope
Implement:

- auth provider adapter boundary
- normalized `AuthenticatedIdentity`
- normalized `SessionContext`
- product authorization input objects
- request-context auth resolution

#### Required source alignment
This stage must use:
- `03_authentication_decision.md`
- `auth_adapter_contract.md`

#### Deliverables
- auth adapter module
- request auth extraction layer
- normalized identity/session objects
- basic authorization gate helpers for workspace/run scope

#### Done criteria
- route handlers consume normalized auth context only
- provider-specific SDK objects stay behind the adapter
- auth identity can be linked to workspace ownership checks

---

### Stage 3 — Database and Migration Foundation

#### Goal
Create the canonical persistence base for workspaces, runs, continuity, and indexed engine outputs.

#### Why third
The server needs stable persistence before run launch, status, and result APIs can become real.

#### Scope
Implement:

- PostgreSQL connection foundation
- migration tooling foundation
- initial schema families for:
  - workspace registry
  - run records
  - artifact metadata/index rows
  - trace summary/index rows
  - onboarding/product continuity rows
- lineage-aware foreign-key/reference design where applicable

#### Required source alignment
This stage must use:
- `02_database_decision.md`
- `database_append_only_lineage_persistence_contract.md`
- `run_record_persistence_contract.md`
- `artifact_persistence_and_retrieval_contract.md`
- `trace_persistence_and_query_contract.md`

#### Deliverables
- migration setup
- first migration set
- schema naming and table family rules
- append-only vs mutable projection separation

#### Done criteria
- migrations run cleanly on a fresh database
- mutable projection tables and append-oriented tables are clearly separated
- run/artifact/trace/workspace linkage is queryable
- DB design does not casually violate append-only or lineage rules

---

### Stage 4 — Run Admission Path

#### Goal
Make `POST /api/runs` real in a boundary-safe way.

#### Why fourth
Run launch is the first product action that truly crosses from server product layer into engine execution.

#### Scope
Implement:

- run launch route
- product-layer validation and authorization
- launch-target lookup
- conversion into `EngineRunLaunchRequest`
- accepted/rejected boundary handling
- run record creation/update at launch time

#### Required source alignment
This stage must use:
- `run_launch_api_contract.md`
- `engine_server_boundary_contract.md`
- `run_record_persistence_contract.md`

#### Deliverables
- `POST /api/runs`
- boundary-safe launch service
- product-layer vs engine-layer error separation
- initial run-record write path

#### Done criteria
- a valid request can create an admitted run
- product-layer failures are distinct from engine-layer rejections
- no execution meaning is invented by the route layer

---

### Stage 5 — Worker / Queue Orchestration

#### Goal
Implement the async execution backbone that turns admitted runs into actual engine work.

#### Why fifth
A run launch API without worker orchestration is only half real.
But worker implementation should come after adapters, auth, and DB foundation are stable.

#### Scope
Implement:

- queue submission
- worker claim/lease model
- heartbeat updates
- orphaned-run detection
- engine invocation through the approved adapter boundary
- terminal result persistence flow
- worker-side observability

#### Required source alignment
This stage must use:
- `worker_execution_contract.md`
- `engine_boundary_type_mapping.md`
- `run_record_persistence_contract.md`

#### Deliverables
- queue producer path
- worker consumer path
- claim lease + heartbeat path
- orphan recovery policy implementation
- result/trace/artifact projection writes from worker side

#### Done criteria
- admitted runs can progress from queued to terminal states
- worker infra failure is distinguishable from engine execution failure
- stale running claims can be detected and handled
- duplicate canonical execution is prevented under normal retry/claim conditions

---

### Stage 6 — Run Status and Result Read APIs

#### Goal
Expose stable read surfaces for current run state and run outcome.

#### Why sixth
Once launch and worker orchestration exist, the first product-readable value must be status and result.

#### Scope
Implement:

- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/result`

#### Required source alignment
This stage must use:
- `run_status_api_contract.md`
- `run_result_api_contract.md`

#### Deliverables
- status route
- result route
- product-safe status projection
- result envelope projection
- correct not-ready / ready-success / ready-partial / ready-failure behavior

#### Done criteria
- clients can poll status safely
- clients can read result without requiring deep artifact inspection
- partial vs failed vs completed remain distinct

---

### Stage 7 — Artifact and Trace Query Surfaces

#### Goal
Expose deeper engine-output observability and retrieval without corrupting truth boundaries.

#### Why seventh
These are important, but they should come after the main launch/status/result loop works end to end.

#### Scope
Implement:

- run artifact list surface
- single artifact retrieval surface
- run trace surface
- summary and paginated event retrieval where needed

#### Required source alignment
This stage must use:
- `artifact_persistence_and_retrieval_contract.md`
- `trace_persistence_and_query_contract.md`

#### Deliverables
- artifact list/query endpoint(s)
- single artifact retrieval endpoint
- trace summary/event endpoint(s)
- payload access policy path

#### Done criteria
- artifacts remain append-only in meaning
- trace ordering is preserved
- status/result endpoints are not overloaded into fake artifact/trace browsers

---

### Stage 8 — Product Continuity Layer

#### Goal
Implement account/workspace return-use continuity beyond single-run execution.

#### Why eighth
This is where Phase 4.5 starts feeling like a real service rather than just a remote run wrapper.

#### Scope
Implement:

- workspace registry queries
- owned/recent workspaces
- recent runs/results
- onboarding continuity
- first-success or unlock continuity if applicable
- multi-device continuity basics

#### Required source alignment
This stage must use:
- `06_mobile_web_session_continuity_decision.md`
- `phase45_architecture_summary.md`
- `run_record_persistence_contract.md`

#### Deliverables
- workspace list/read surfaces
- recent activity surfaces
- onboarding continuity persistence and retrieval
- server-authoritative continuity rules in practice

#### Done criteria
- a user can return on another device and recover workspace/run continuity from server truth
- local `.nex.ui` remains convenience only, not canonical continuity

---

### Stage 9 — Secret / Provider Server Integration

#### Goal
Implement canonical server-side provider and secret usage under the chosen infrastructure model.

#### Why ninth
This should come after the engine/server seam, DB, runs, and worker flow are already real.
Otherwise secret/provider design tends to sprawl prematurely.

#### Scope
Implement:

- AWS Secrets Manager integration
- server-side secret fetch boundary
- provider access policy checks
- separation between local/dev bridge credentials and canonical product credentials

#### Required source alignment
This stage must use:
- `04_secret_and_provider_credential_decision.md`
- `auth_adapter_contract.md`
- `engine_server_boundary_contract.md`

#### Deliverables
- secret authority integration
- provider policy resolution path
- clear product-vs-local credential split

#### Done criteria
- server-side canonical credentials no longer depend on local env assumptions
- local/dev bridge and canonical SaaS path are clearly separated in code

---

### Stage 10 — Hardening and Consistency Review

#### Goal
Close the loop by checking that the implementation still matches the design set.

#### Why tenth
Phase 4.5 is exactly the sort of stage where drift can accumulate if not re-audited before larger product work continues.

#### Scope
Review and verify:

- no route handler drift around adapters
- no auth leakage into engine-core
- no artifact append-only violations
- no trace synthesis
- no accidental softening of engine failure truth
- DB schema and migration practice still align with the documented contracts

#### Deliverables
- implementation audit checklist
- drift list if needed
- contract sync corrections if needed

#### Done criteria
- implementation remains aligned with the current document set
- Phase 4.5 foundation is stable enough to support later product work without architectural backtracking

## 5. Recommended First Real Coding Start

If only one coding start point is chosen, start here:

**Stage 1 — Engine/Server Adapter Foundation**

Reason:
- it is the narrowest seam
- it reduces future coupling risk the most
- every later server feature depends on it

## 6. What Not To Do First

The following are specifically discouraged as first implementation moves:

1. building many API routes before adapters exist
2. wiring Clerk directly into engine-facing code
3. writing worker logic before claim/lease/status rules are fixed
4. exposing artifact/trace endpoints before run launch/status/result loop exists
5. treating product continuity UI needs as justification for bypassing engine/server boundary discipline

## 7. Practical Summary

The shortest correct implementation path is:

1. adapters
2. auth abstraction
3. DB + migrations
4. run launch
5. worker lifecycle
6. status/result reads
7. artifact/trace reads
8. continuity layer
9. secrets/provider integration
10. hardening review

That order is designed to maximize:
- architectural safety
- testability
- incremental validation
- low rework risk

## 8. Final Statement

Phase 4.5 is now documented well enough that the main remaining question is no longer "what architecture should we choose?"

The main remaining question is:

"in what order should we implement the already-chosen architecture so we do not damage Nexa's core engine model?"

This document answers that question.
