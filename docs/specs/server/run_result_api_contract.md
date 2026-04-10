# Run Result API Contract v1

## Recommended save path
`docs/specs/server/run_result_api_contract.md`

## 1. Purpose

This document defines the canonical API contract for reading Nexa run results through the server layer.

Its purpose is to make the following boundary explicit:

- clients do not inspect raw engine result internals directly
- clients request run results through the server
- the server returns a product-facing projection of canonical engine result truth
- result transport must remain traceable to engine-owned execution/artifact truth
- summary fields may be added, but engine meaning must not be rewritten

This contract follows:
- Engine ↔ Server Layer Boundary Contract
- Run Launch API Contract
- Run Status API Contract

## 2. Core Decision

Run result is engine-owned outcome truth exposed through a server-owned retrieval surface.

Official rule:

- the engine owns final result meaning
- the server owns the query endpoint and product-facing transport shape
- the server may summarize and enrich
- the server may not invent success, partiality, failure, or outputs

In short:

The engine decides what came out.
The server decides how product clients receive it safely.

## 3. API Endpoint

Canonical endpoint:

`GET /api/runs/{run_id}/result`

This endpoint returns the current canonical result envelope for a run.

## 4. Result Availability Rule

A result may exist in several states:

- `not_ready`
- `ready_success`
- `ready_partial`
- `ready_failure`

Important:
- `not_ready` means no canonical final result envelope is available yet
- `ready_failure` still represents a valid result envelope if the engine has produced a canonical failed terminal state
- the server must not pretend a missing result is ready

## 5. Recommended Response Shape

Recommended response object:

    {
      "run_id": "run_001",
      "workspace_id": "ws_123",
      "result_state": "ready_success",
      "final_status": "completed",
      "result_summary": {
        "title": "Review completed",
        "description": "The circuit produced a reviewed answer with confidence output."
      },
      "final_output": {
        "output_key": "result",
        "value_preview": "The document argues that...",
        "value_type": "text"
      },
      "artifact_refs": [
        {
          "artifact_id": "art_001",
          "kind": "final_output",
          "label": "Reviewed answer"
        }
      ],
      "trace_ref": {
        "run_id": "run_001",
        "endpoint": "/api/runs/run_001/trace"
      },
      "metrics": {
        "duration_ms": 12440,
        "cost_estimate": 0.08
      },
      "updated_at": "2026-04-10T12:02:00Z"
    }

## 6. Field Semantics

### 6.1 `result_state`
Product-facing readiness label.

Recommended values:
- `not_ready`
- `ready_success`
- `ready_partial`
- `ready_failure`

### 6.2 `final_status`
Canonical terminal status from engine truth where available.

Recommended values:
- `completed`
- `partial`
- `failed`

### 6.3 `result_summary`
A concise product-facing explanation.
May summarize canonical engine outcome.
Must not contradict canonical status.

### 6.4 `final_output`
A compact representation of the primary result.
This is not required to carry every artifact payload.
It is the main product-facing final output projection.

### 6.5 `artifact_refs`
References to canonical artifacts related to the run result.

### 6.6 `trace_ref`
Pointer to the trace surface for deeper temporal inspection.

### 6.7 `metrics`
Optional normalized product-facing metrics.
May include duration/cost style summaries.
Must remain clearly derived, not invented.

## 7. Product-layer vs Engine-layer Meaning

The server may add:
- summary text
- preview fields
- retrieval links
- workspace linkage
- safe UI convenience groupings

The server may not change:
- whether a result exists
- whether the run completed, failed, or is partial
- what artifacts were actually produced
- what the primary canonical output means

## 8. Failure Response Families

### 8.1 Product-layer read failure
Examples:
- unauthenticated
- forbidden
- run not visible to caller
- malformed request

These are server-owned.

### 8.2 Result not ready
Recommended response shape:

    {
      "run_id": "run_001",
      "result_state": "not_ready",
      "message": "The run result is not available yet."
    }

### 8.3 Canonical failed result
A failed run may still have a result envelope.
Do not collapse failed result into "not found".

## 9. Relationship to Status

Official rule:
- status endpoint answers: what state is the run in now?
- result endpoint answers: what outcome does this run currently expose?

The result endpoint may repeat terminal status, but it is not the general polling surface.

## 10. Relationship to Artifacts

The result endpoint is allowed to expose:
- primary output preview
- artifact references
- lightweight summaries

It must not become a full artifact browser.
Deep artifact inspection belongs to artifact retrieval/query surfaces.

## 11. What Must Never Happen

The following are forbidden:

1. server reporting success result without canonical engine success truth
2. server hiding partial result behind false success wording
3. server inventing final output from client/UI hints
4. artifact references being omitted in a way that hides canonical outputs
5. failed terminal result being flattened into generic "not found"

## 12. Final Statement

The Run Result API in Nexa is the product-facing retrieval surface for canonical engine outcomes.

The engine owns the outcome.
The server exposes it in a safe, queryable form.

That boundary must remain explicit if Nexa is to preserve execution truth at scale.
