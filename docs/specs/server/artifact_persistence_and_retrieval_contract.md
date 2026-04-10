# Artifact Persistence and Retrieval Contract v1

## Recommended save path
`docs/specs/server/artifact_persistence_and_retrieval_contract.md`

## 1. Purpose

This document defines how canonical engine-originated artifacts are persisted, indexed, and retrieved through the server/product layer.

Its purpose is to preserve the append-only artifact rule while still allowing product-facing retrieval, previews, and history queries.

## 2. Core Decision

Artifacts are engine-originated append-only outputs.

Official rule:

- the engine creates artifact truth
- the server persists artifact references, indexes, metadata, and allowed payload storage
- the server may expose retrieval/query surfaces
- the server must not mutate canonical artifact meaning after creation

## 3. Artifact Categories

Recommended categories:
- `final_output`
- `intermediate_output`
- `diagnostic`
- `trace_linked`
- `delivery_related`
- `evaluation_related`

These are retrieval/index labels, not new execution semantics.

## 4. Persistence Split

Recommended persistence model:

### 4.1 PostgreSQL
Use for:
- artifact ids
- run/workspace linkage
- artifact kind/type
- timestamps
- integrity metadata
- lineage references
- search/index metadata
- safe previews/summaries where appropriate

### 4.2 Blob/Object Storage
Use when needed for:
- large payloads
- binary payloads
- documents/media
- bulky structured outputs

Recommended principle:
- PostgreSQL is the metadata/query authority
- blob storage is the payload authority when artifact size or volume requires it

## 5. Retrieval Surfaces

Recommended endpoint families:

- `GET /api/runs/{run_id}/artifacts`
- `GET /api/artifacts/{artifact_id}`
- later optional filtered/query endpoints

### 5.1 List surface
Returns artifact summaries/refs for a run.

### 5.2 Single artifact surface
Returns canonical metadata + allowed payload access form.

## 6. Recommended Artifact Summary Shape

    {
      "artifact_id": "art_001",
      "run_id": "run_001",
      "workspace_id": "ws_123",
      "kind": "final_output",
      "label": "Reviewed answer",
      "value_type": "text",
      "preview": "The document argues that...",
      "created_at": "2026-04-10T12:02:00Z"
    }

## 7. Recommended Single Artifact Retrieval Shape

    {
      "artifact_id": "art_001",
      "run_id": "run_001",
      "workspace_id": "ws_123",
      "kind": "final_output",
      "label": "Reviewed answer",
      "value_type": "text",
      "payload_access": {
        "mode": "inline",
        "value": "Full reviewed answer text..."
      },
      "integrity": {
        "append_only": true
      },
      "created_at": "2026-04-10T12:02:00Z"
    }

Payload access modes may later include:
- `inline`
- `download`
- `signed_url`
- `reference_only`

## 8. Append-only Rule

The append-only rule must be visible at the persistence level.

Recommended rules:

- canonical artifact rows are never overwritten with new semantic content
- payload replacements that change canonical meaning are forbidden
- corrections/new derivations produce new artifacts, not silent mutation of old artifacts
- preview caches may be regenerated, but canonical artifact identity and meaning must remain stable

## 9. Lineage Rule

Artifacts should be query-linked to:
- run id
- workspace id
- source node if available
- upstream/downstream refs where appropriate

This is lineage/indexing support.
It must not become informal semantic rewriting.

## 10. Authorization Rule

Artifact retrieval is server/product authorized.

Recommended rule:
- caller must have access to the parent workspace/run scope
- possession of artifact id alone is not sufficient authorization

## 11. What Must Never Happen

The following are forbidden:

1. mutating canonical artifact meaning after creation
2. treating preview text as the canonical artifact payload when it is only a summary
3. storing giant artifact payloads only in query tables when object storage is the rational design
4. letting client-side UI state redefine artifact identity
5. detaching artifacts from run/workspace lineage

## 12. Final Statement

Artifacts in Nexa are append-only engine outputs.

The server may persist and expose them.
It may not rewrite them.

That rule must remain explicit if product retrieval is to coexist with canonical artifact truth.
