# Engine Boundary Type Mapping v1

## Recommended save path
`docs/specs/server/engine_boundary_type_mapping.md`

## 1. Purpose

This document defines how the server-side boundary objects introduced for Phase 4.5 map onto the current documented Nexa engine-side interfaces and model families.

Its purpose is to prevent the creation of two parallel type systems:

- one in the engine
- one in the server contracts

This document does not invent a new engine architecture.
It only explains how the new server boundary objects should attach to the existing engine-facing candidates already identified in the review.

## 2. Why This Document Exists

The current server contract set introduced boundary object families such as:

- `EngineRunLaunchRequest`
- `EngineRunLaunchResponse`
- `EngineRunStatusSnapshot`
- `EngineResultEnvelope`
- `EngineValidationEnvelope`

Claude's review identified the main remaining gap correctly:

the boundary objects are directionally valid, but they were not yet mapped to the current documented engine-side classes and interfaces. The review named the key current candidates as:

- `CircuitRunner`
- `ExecutionRecord`
- `ValidationFinding`
- trace model
- Artifact model

That gap must be closed before implementation to avoid ad hoc conversion logic spreading across the codebase.

## 3. Core Decision

Boundary objects are transport and integration objects.

Official rule:

- boundary objects are not a second engine model family
- boundary objects are normalized integration-layer projections
- each boundary object must map to an existing engine-side interface, model, or model family
- when the engine already has a canonical model, the server boundary must wrap or project it rather than redefining it

In short:

The server layer may normalize engine truth.
It may not create a competing truth vocabulary.

## 4. Mapping Scope

This mapping covers the current server-facing boundary object families introduced in the Phase 4.5 contracts.

It does not attempt to map every engine-internal class.
It maps only the objects that cross or sit directly next to the Engine ↔ Server boundary.

## 5. Canonical Mapping Table

| Boundary Object | Current Documented Engine-side Candidate | Mapping Purpose | Required Adapter / Notes |
|---|---|---|---|
| `EngineRunLaunchRequest` | `CircuitRunner.run()` input candidate | normalize server launch request into current engine execution entry input | thin engine launch adapter required |
| `EngineRunLaunchResponse` | launch acceptance/rejection outcome around current run invocation boundary | normalize whether engine accepted execution start | thin launch-result wrapper required |
| `EngineRunStatusSnapshot` | current run-status projection family; current documented status truth is ultimately engine-owned and surfaced to UI through execution status projections | expose concise current run status without exposing raw internals directly | server status adapter required |
| `EngineResultEnvelope` | `ExecutionRecord` candidate | expose canonical result/status/artifact linkage in product-safe form | execution-record-to-result adapter required |
| `EngineValidationEnvelope` | `ValidationFinding` / validation finding collection candidate | preserve canonical validation severity/code/message truth | validation finding normalization adapter required |
| trace events | `trace.py` event model candidate | preserve canonical event ordering and event type meaning | trace-event mapping adapter required |
| artifact refs | current Artifact model candidate | expose artifact identity, kind, linkage, and retrieval refs | artifact reference projection adapter required |

## 6. Mapping Interpretation Rules

### 6.1 `EngineRunLaunchRequest` → `CircuitRunner.run()` input candidate

Meaning:
- the server accepts a product-facing run request
- the server normalizes that request into `EngineRunLaunchRequest`
- a thin engine launch adapter transforms that normalized boundary object into whatever the current `CircuitRunner.run()` input contract requires

Important:
- this mapping layer must be thin
- hidden structural mutation is forbidden
- product context may be added as normalized metadata/reference, not as execution-semantics redefinition

### 6.2 `EngineRunLaunchResponse` → launch boundary outcome

Meaning:
- the boundary object should capture whether engine-side launch/start was accepted or rejected
- this should wrap, not replace, the actual engine-side start decision

Important:
- a server-side "accepted into queue" state must not be confused with canonical engine execution truth
- if the engine rejects start, that rejection must remain visible as engine-owned

### 6.3 `EngineRunStatusSnapshot` → current engine-owned run status projection

Meaning:
- this boundary object is a concise server-safe view of engine-owned status truth
- it is not a new source of status meaning

Recommended content mapping:
- status
- active node summary if available
- latest warning/failure signal if available
- progress only when truthfully available

Important:
- fake progress is forbidden
- `unknown` is allowed only for true visibility gaps

### 6.4 `EngineResultEnvelope` → `ExecutionRecord` candidate

Meaning:
- the server-facing result envelope should be built from the engine's canonical result/history record family
- the review explicitly identified `ExecutionRecord` as the current documented candidate

Recommended mapping family:
- final status → terminal result status
- output summary → selected final output projection
- artifact refs → linked artifact identities
- trace refs → linked trace/timeline retrieval path
- metrics/timing → derived only from canonical engine-known values

Important:
- failed and partial terminal states must remain distinct
- a failed run may still produce a valid result envelope

### 6.5 `EngineValidationEnvelope` → `ValidationFinding` candidate

Meaning:
- validation/precheck result transport should be built from the current validation finding family rather than reinvented

Recommended mapping family:
- severity → preserve canonical severity
- code → preserve machine-usable code
- message → preserve or safely wrap canonical meaning
- finding location/context → preserve where available

Important:
- product-facing wording may be simplified
- severity/code semantics must not be softened or collapsed

### 6.6 trace events → trace model candidate

Meaning:
- server trace query surfaces must be built on top of the current trace event model family
- event ordering and event type meaning remain engine-originated

Recommended mapping family:
- event id
- event type
- ordering / sequence
- timestamp
- node linkage if available
- severity/message if available

Important:
- missing canonical events must never be synthesized
- summary views must remain traceable back to canonical event rows/payloads

### 6.7 artifact refs → Artifact model candidate

Meaning:
- the server artifact surfaces should expose references derived from the current Artifact model family

Recommended mapping family:
- artifact id
- artifact kind/type
- run linkage
- lineage linkage
- optional payload access mode
- optional integrity/hash metadata if present

Important:
- artifact preview is not canonical payload replacement
- append-only meaning must remain stable after creation

## 7. Required Adapters

This mapping implies a small, explicit adapter set.

Recommended adapter names:

1. `EngineLaunchAdapter`
2. `ExecutionRecordResultAdapter`
3. `ValidationFindingAdapter`
4. `TraceEventAdapter`
5. `ArtifactReferenceAdapter`
6. `EngineStatusProjectionAdapter`

These names may change in implementation, but the separation of responsibilities should remain.

## 8. Adapter Design Rules

### 8.1 Thin mapping rule
Adapters should map, not reinterpret.

### 8.2 One responsibility rule
Each adapter should handle one boundary family.

### 8.3 No hidden semantics rule
Adapters must not introduce new engine meaning not present in canonical engine-side truth.

### 8.4 Stable error family rule
Adapters must preserve whether a failure belongs to:
- product/server layer
- engine layer

## 9. Mapping Confidence Levels

This document is based on the currently documented engine-side candidates explicitly named in the review:

- `CircuitRunner`
- `ExecutionRecord`
- `ValidationFinding`
- trace model
- Artifact model

Therefore:

- the mapping direction is firm
- exact field-by-field implementation still requires verification against the latest actual code
- implementation must confirm the final field correspondence before coding adapters

This is not a weakness.
It is the correct design order:

direction first, exact code binding second.

## 10. Implementation Checklist

Before coding server adapters, verify:

1. what `CircuitRunner.run()` currently receives
2. what object currently represents canonical execution result/history
3. what validation finding shape is canonical now
4. what the current trace event fields/enums are
5. what artifact identity/hash/lineage fields already exist
6. whether any existing adapter/projection code already partially solves one of these mappings

## 11. What Must Never Happen

The following are forbidden:

1. inventing a second result model that diverges from `ExecutionRecord`
2. duplicating validation semantics instead of projecting `ValidationFinding`
3. creating free-form trace event transport detached from the canonical trace model
4. treating adapter DTOs as a new source of engine truth
5. spreading field-mapping logic ad hoc across route handlers, workers, and persistence code

## 12. Final Statement

The role of this document is simple:

server boundary objects must attach cleanly to the current documented engine-side candidates.

They are integration objects, not rival engine types.

That mapping must remain explicit if Phase 4.5 implementation is to stay aligned with Nexa's architecture.
