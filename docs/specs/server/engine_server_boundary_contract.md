# Engine ↔ Server Layer Boundary Contract v1

## Recommended save path
`docs/specs/server/engine_server_boundary_contract.md`

## 1. Purpose

This document defines the canonical boundary between:

- the Nexa engine layer
- the Phase 4.5 server/product layer

Its purpose is to prevent ad hoc coupling between Nexa's execution architecture and its future SaaS/mobile backend.

This contract exists because the Phase 4.5 gate decisions define the infrastructure direction,
but infrastructure decisions alone do not explain how the server layer may interact with:

- Circuit
- Node
- Runtime
- Artifact
- Trace

Without this boundary, Phase 4.5 implementation risks eroding Nexa's core architectural invariants.

## 2. Core Decision

The server layer is not allowed to redefine the engine.

Official rule:

- the engine owns execution truth
- the server owns product-facing delivery, persistence, identity binding, and remote access surfaces
- the server may orchestrate, persist, query, and expose engine outcomes
- the server may not silently rewrite engine semantics

In short:

The engine decides what happened.
The server decides how product users access, persist, and continue from what happened.

## 3. Canonical Layer Split

Official layered model:

User / Client
→ Server Product Layer
→ Engine Invocation Boundary
→ Nexa Engine
→ Engine Truth Outputs
→ Server Persistence / Query / Delivery Layer
→ Client-facing Product Surfaces

### 3.1 User / Client Layer
Examples:
- web app
- mobile app
- future external integrations

This layer:
- collects user intent
- reads product state
- submits allowed product actions

This layer must not:
- own execution truth
- fabricate trace/artifact truth
- directly mutate canonical engine artifacts

### 3.2 Server Product Layer
Examples:
- REST API
- auth-bound route handling
- workspace registry
- run launch/status/result endpoints
- onboarding continuity
- delivery/integration surfaces

This layer:
- authenticates the user
- authorizes product actions
- maps product actions into engine-facing requests
- stores product-facing history and continuity
- exposes product-facing queries

This layer must not:
- redefine Node semantics
- skip the engine and invent execution outcomes
- rewrite canonical artifact/trace meaning

### 3.3 Engine Invocation Boundary
This is the formal bridge between product/backend code and engine code.

It must define:
- what input is needed to launch a run
- what input is needed to inspect a saved structure
- what outputs come back from the engine
- what findings/status objects are canonical
- what error/result contracts cross the boundary

This boundary must be explicit and typed.

### 3.4 Nexa Engine
The engine owns:

- circuit structure semantics
- node execution semantics
- dependency-based execution
- runtime truth
- artifact truth
- trace truth
- validation truth
- proposal/approval truth where applicable

The engine is the only layer allowed to determine canonical execution meaning.

### 3.5 Server Persistence / Query / Delivery Layer
After engine truth exists, the server layer may:

- persist run metadata
- persist result references
- persist artifact references or selected artifact payload policy outputs
- persist trace indexes or summaries
- store workspace/run/result continuity
- expose query models for product reuse
- trigger approved downstream delivery actions

But this layer must still preserve engine truth rather than reinterpret it.

## 4. Non-Negotiable Invariants

The following must remain unchanged:

### 4.1 Node remains the sole execution unit
The server may queue jobs or track runs, but it must not redefine a new execution unit above or below Node.

### 4.2 Dependency-based execution remains canonical
The server may launch or observe execution, but it must not replace dependency-based execution semantics with ad hoc route logic.

### 4.3 Artifact truth remains engine-originated
The server may store, index, and retrieve artifact references and allowed payload forms, but it must not fabricate artifacts as if they were engine outputs.

### 4.4 Trace truth remains engine-originated
The server may persist trace data and expose trace query surfaces, but it must not invent missing trace events.

### 4.5 UI/local continuity is not canonical product continuity
Local `.nex.ui` comfort state remains local convenience only.
Server-side continuity for account/workspace/run/result state remains distinct.

### 4.6 Approval and validation truth remain canonical
The server may expose approval and validation state, but it must not soften or reinterpret blocked/pass semantics into false success.

## 5. What the Engine Owns

The engine owns the meaning of:

- Circuit
- Node
- Resource execution inside a Node
- runtime scheduling according to Nexa runtime rules
- validation findings
- proposal/precheck/preview/approval chain where applicable
- artifact creation
- trace event production
- final execution result status

The server may read, persist, and expose these truths.
It may not redefine them.

## 6. What the Server Owns

The server owns the product-layer meaning of:

- authenticated user identity binding
- workspace registry
- workspace list/read/write API access
- run launch request routing
- run status polling/subscription surfaces
- result history queries
- onboarding continuity
- provider/accounting/product policy surfaces
- delivery/integration routing
- quota/accounting enforcement at the product layer
- multi-device continuity

The server is therefore the owner of product continuity, not execution semantics.

## 7. Canonical Boundary Objects

The boundary should be expressed through explicit typed objects.

Recommended object families:

### 7.1 EngineRunLaunchRequest
Represents the minimal typed request the server may send to the engine to start a run.

Should include:
- run request id
- authenticated product context reference
- target save/snapshot reference
- explicit execution target
- allowed runtime options
- optional input payload binding
- correlation metadata

Should not include:
- hidden server-only business logic masquerading as runtime semantics

### 7.2 EngineRunLaunchResponse
Represents the immediate engine-facing response after a launch request is accepted or rejected.

Should include:
- accepted/rejected status
- canonical run identity
- initial execution status
- blocking findings if launch is refused

### 7.3 EngineRunStatusSnapshot
Represents a typed read model of current engine-known run status.

Should include:
- run status
- active node summary if any
- progress summary if available
- latest warnings/errors
- trace/artifact summary refs if available

### 7.4 EngineResultEnvelope
Represents the canonical result package the server may persist and expose after a run.

Should include:
- run id
- final status
- result summary
- artifact refs
- trace refs or summaries
- timing/cost metrics when applicable
- canonical failure information if failed/partial

### 7.5 EngineValidationEnvelope
Represents canonical validation/precheck output exposed through the server layer without reinterpretation.

## 8. Run Launch Boundary

Official rule:

- clients do not launch the engine directly
- clients call the server
- the server validates auth/product-level permissions
- the server constructs an engine-facing launch request
- the engine accepts or rejects the launch according to engine truth
- the server records and exposes the resulting run identity and status

Meaning:
- server authorization comes before launch
- engine execution truth comes after launch
- neither layer replaces the other

## 9. Run Status and Result Boundary

Official rule:

- the engine determines run status truth
- the server persists and exposes queryable status/result continuity

Therefore:
- `/api/runs/*` may expose a product-friendly projection
- but that projection must remain traceable back to canonical engine result/status truth

The server may summarize.
It may not falsify.

## 10. Artifact Boundary

Official rule:

- artifacts are engine-originated append-only outputs
- the server may persist artifact references, indexes, summaries, and approved retrieval paths
- the server may also store selected payload forms according to explicit policy
- the server must not mutate canonical artifact meaning after creation

Recommended rule:
- treat the database as an index/metadata authority for artifacts
- treat object/blob storage as the likely payload authority once artifact sizes or counts grow
- keep the append-only rule visible at the persistence design level

## 11. Trace Boundary

Official rule:

- trace events are engine-originated
- the server may store trace summaries, searchable indexes, and canonical event payloads
- the server may expose timeline/query surfaces
- the server must not synthesize missing canonical events

Recommended rule:
- product APIs may expose both summary and deep inspection views
- both must remain traceable to engine-originated trace truth

## 12. Database Responsibility Rule

The database is a persistence and query layer, not a semantic authority.

Meaning:
- PostgreSQL stores product continuity and indexed engine outputs
- PostgreSQL does not become the place where execution meaning is invented
- append-only, status, and lineage rules must be respected by schema design rather than assumed informally

## 13. Auth Responsibility Rule

Authentication is a server/product concern, not an engine concern.

Meaning:
- the engine should not depend on Clerk-specific concepts internally
- the server maps authenticated product identity into engine launch context
- auth provider choice must remain outside engine-core semantics

Recommended implementation consequence:
- use an auth abstraction/adapter layer at the server boundary

## 14. Error Responsibility Rule

Errors must be separated by layer:

### 14.1 Product-layer errors
Examples:
- unauthenticated
- forbidden
- quota exhausted
- invalid route input
- missing workspace access

These are server-owned.

### 14.2 Engine-layer errors
Examples:
- validation blocked
- execution failed
- provider/runtime failure
- canonical run failure state
- engine-originated partial result state

These are engine-owned.

The server may wrap these for transport, but must preserve which layer produced them.

## 15. What Must Never Happen

The following are forbidden:

1. the server inventing successful run completion without canonical engine result
2. the database becoming the informal source of execution semantics
3. auth provider types leaking into engine-core contracts
4. local `.nex.ui` continuity being treated as canonical product continuity
5. the server rewriting blocked validation into false pass/readiness
6. trace reconstruction guesses being presented as canonical trace truth
7. delivery/integration side effects being mistaken for engine execution truth
8. product route handlers directly mutating engine-owned artifacts outside the official boundary

## 16. Immediate Design Consequence

Before broad Phase 4.5 implementation proceeds, the following contracts should be derived from this boundary:

1. Engine Run Launch API Contract
2. Run Status / Result API Contract
3. Artifact Persistence and Retrieval Contract
4. Trace Persistence and Query Contract
5. Auth Adapter Contract
6. Database Append-Only / Lineage Persistence Contract

## 17. Final Statement

The Engine ↔ Server boundary in Nexa is simple in principle:

- the engine owns execution meaning
- the server owns product access, persistence, continuity, and exposure

The server may coordinate and preserve engine truth.
It may not redefine that truth.

That boundary must remain explicit if Phase 4.5 is to scale without eroding Nexa's architecture.
