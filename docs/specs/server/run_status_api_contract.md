# Run Status API Contract v1

## Recommended save path
`docs/specs/server/run_status_api_contract.md`

## 1. Purpose

This document defines the canonical API contract for reading Nexa run status through the server layer.

Its purpose is to make the following boundary explicit:

- clients do not inspect raw engine internals directly
- clients request run status through the server
- the server returns a product-facing projection of canonical engine run truth
- the returned projection must remain traceable back to engine-owned status truth
- product-layer metadata may be added, but engine meaning must not be rewritten

This contract exists as a direct follow-up to:

- Engine ↔ Server Layer Boundary Contract
- Run Launch API Contract

## 2. Core Decision

Run status is engine-owned truth exposed through a server-owned query surface.

Official rule:

- the engine owns canonical run state
- the server owns the query endpoint and product-facing transport shape
- the server may summarize and enrich
- the server may not fabricate status transitions or hide engine-owned failure/blocking states

In short:

The engine decides what state the run is in.
The server decides how clients read that state safely and consistently.

## 3. Position in the Overall Flow

Canonical flow:

Client
→ GET /api/runs/{run_id}
→ Server auth / authorization / lookup
→ Engine-originated run state + persisted run projection lookup
→ Product-facing status response
→ Client UI updates status display / polling / subscription logic

This contract covers the canonical status-read boundary.

## 4. API Endpoint

Canonical endpoint:

`GET /api/runs/{run_id}`

This endpoint returns the current known product-facing status projection for a single run.

## 5. Canonical Status Rule

The product-facing status must remain compatible with canonical engine status truth.

Recommended primary status family:

- `queued`
- `starting`
- `running`
- `completed`
- `failed`
- `cancelled`
- `partial`
- `unknown`

Important rules:

- `completed` means the engine reached a canonical completed state
- `failed` means the engine reached a canonical failed state
- `partial` means the engine reports incomplete/partial result truth
- `unknown` is only for exceptional visibility gaps and must not be used to hide known status
- the server must not invent softer product wording that contradicts engine truth

## 6. Request Semantics

### 6.1 Path parameter

`run_id`

Represents the canonical run identity returned by launch acceptance.

### 6.2 Authentication and authorization

Before returning status, the server must verify:

- the caller is authenticated for canonical product status access
- the caller is allowed to read the requested run in its workspace/account scope

If not, the server must reject at the product layer before returning any run information.

## 7. Recommended Response Shape

Recommended response object:

    {
      "run_id": "run_001",
      "workspace_id": "ws_123",
      "execution_target": {
        "target_type": "commit_snapshot",
        "target_ref": "snap_456"
      },
      "status": "running",
      "status_family": "active",
      "created_at": "2026-04-10T12:00:00Z",
      "started_at": "2026-04-10T12:00:02Z",
      "updated_at": "2026-04-10T12:00:25Z",
      "progress": {
        "percent": 42,
        "active_node_id": "review_bundle",
        "active_node_label": "Review Bundle",
        "summary": "Running review stage"
      },
      "latest_engine_signal": {
        "severity": "info",
        "code": "NODE_RUNNING",
        "message": "Review Bundle is currently executing."
      },
      "links": {
        "result": "/api/runs/run_001/result",
        "trace": "/api/runs/run_001/trace",
        "artifacts": "/api/runs/run_001/artifacts"
      }
    }

## 8. Field Semantics

### 8.1 Identity fields

#### `run_id`
Canonical run identity.

#### `workspace_id`
Product-facing workspace scope for authorization and continuity.

#### `execution_target`
The target the run was launched against.

This must remain traceable to launch-time execution target truth.

### 8.2 Status fields

#### `status`
Canonical product-facing status label derived from engine truth.

#### `status_family`
Optional product grouping for UI convenience.

Recommended families:
- `pending`
- `active`
- `terminal_success`
- `terminal_failure`
- `terminal_partial`
- `unknown`

This grouping is allowed only if it does not distort canonical status truth.

### 8.3 Time fields

Recommended fields:
- `created_at`
- `started_at`
- `updated_at`
- optional later: `completed_at`

The server may expose normalized timestamps for product continuity.
These do not replace canonical engine trace timing.

### 8.4 Progress object

The progress object is optional and must be truthful.

Recommended fields:
- `percent`
- `active_node_id`
- `active_node_label`
- `summary`

Important:
- progress is allowed only when the engine or canonical run projection can support it truthfully
- the server must not invent fake percentages to soothe the user
- if exact progress is unknown, progress may be omitted or represented cautiously

### 8.5 Latest engine signal

This is an optional compact signal summarizing the latest important engine-originated state.

Recommended fields:
- `severity`
- `code`
- `message`

It may summarize:
- latest warning
- active step
- recent failure reason
- completion summary

But it must remain traceable to canonical engine-originated state.

## 9. Data Sources Rule

The server may build the response from:

- canonical persisted run record projection
- canonical engine-originated status updates
- canonical trace-derived status summaries where explicitly allowed

But the server must not build status from:

- guessed UI state
- inferred local `.nex.ui` continuity
- missing/assumed engine events
- optimistic client-side placeholders promoted into truth

## 10. Product-layer vs Engine-layer Meaning

The server may add product-layer information such as:

- workspace linkage
- route links
- safe UI summary text
- polling hints
- product correlation metadata

The server may not change:

- whether the run actually started
- whether the run failed
- whether the run completed
- whether the run is partial
- what the latest canonical blocking/failure signal was

## 11. Failure Response Families

The API must distinguish failure families clearly.

### 11.1 Product-layer read failure
Examples:
- unauthenticated
- forbidden
- run not visible in caller scope
- malformed request

These are server-owned.

### 11.2 Run not found
If the run does not exist in canonical product continuity scope, return not found.

### 11.3 Visibility delay / status unavailable
If the run exists but the status projection is temporarily unavailable, the server may return a bounded visibility-gap response.

Recommended shape:

    {
      "run_id": "run_001",
      "status": "unknown",
      "status_family": "unknown",
      "message": "Run exists, but current status is temporarily unavailable."
    }

Important:
This must only be used when status is genuinely unavailable.
It must not hide a known engine truth.

## 12. Polling / Refresh Semantics

Recommended rule:

- clients may poll `GET /api/runs/{run_id}` for current status
- later push/subscription surfaces may exist, but polling remains canonical and sufficient
- the response must be stable enough for repeated product refresh

The contract should therefore avoid unstable field meaning across requests.

## 13. Relationship to Trace

Run status is not the same as full trace.

Official rule:

- status endpoint gives the concise run state
- trace endpoint gives temporal detail
- status may include a compact latest-engine-signal
- clients requiring deep temporal inspection must use the trace surface

This separation prevents the status endpoint from becoming an overloaded fake-trace surface.

## 14. Relationship to Result

Run status is not the result.

Official rule:

- status endpoint answers: "what state is the run in now?"
- result endpoint answers: "what outcome or final result does this run have?"

A terminal status may include a short summary, but the canonical output/result surface belongs to the result endpoint.

## 15. What Must Never Happen

The following are forbidden:

1. server reporting `completed` without canonical engine completion truth
2. server reporting `running` purely from stale optimistic client state
3. product-layer summary text contradicting engine-owned failure/partial status
4. fake progress percentages presented as if canonical
5. local `.nex.ui` continuity affecting canonical run status
6. flattening `failed` and `partial` into the same ambiguous status
7. using the status endpoint as a substitute for trace or result truth

## 16. Derived Contracts Needed After This

This contract should be followed by:

1. Run Result API Contract
2. Trace Query Contract
3. Artifact Retrieval Contract
4. Run Record Persistence Contract

## 17. Final Statement

The Run Status API in Nexa is a read boundary, not a truth authority.

The engine owns the run state.
The server exposes that state in a product-safe form.

That distinction must remain explicit if Nexa is to scale without corrupting its execution architecture.
