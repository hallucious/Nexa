# Run Record Persistence Contract v1

## Recommended save path
`docs/specs/server/run_record_persistence_contract.md`

## 1. Purpose

This document defines how the server/product layer persists run records for product continuity.

Its purpose is to separate:

- canonical engine run truth
from
- product-facing run continuity/query records

## 2. Core Decision

Run records are server-side persistence/query projections of engine-originated run truth.

Official rule:

- the engine owns run execution meaning
- the server owns run continuity records used for product queries
- run records must remain traceable to canonical engine run identity
- run records must not become an informal replacement for engine semantics

## 3. Why This Contract Exists

Product needs require:
- run history
- workspace run lists
- status lookups
- result retrieval linkage
- account/workspace continuity
- later notifications/delivery linkage

Those needs justify run records.
But run records must not become the place where execution meaning is invented.

## 4. Minimum Run Record Fields

Recommended minimum fields:

- `run_id`
- `workspace_id`
- `execution_target_type`
- `execution_target_ref`
- `requested_by_user_ref`
- `created_at`
- `started_at` optional
- `completed_at` optional
- `current_known_status`
- `current_known_status_family` optional
- `latest_result_state` optional
- `latest_error_family` optional
- `trace_available`
- `artifact_count` optional

## 5. Recommended Rules

### 5.1 Identity rule
`run_id` must remain the canonical linkage key.

### 5.2 Projection rule
The record is a projection of engine truth.
It may lag slightly in transport/persistence timing, but it must not contradict canonical truth.

### 5.3 Query rule
Run records must support:
- list by workspace
- fetch by run id
- filter by status family if needed
- linkage to result/trace/artifact surfaces

### 5.4 Mutation rule
A run record may be updated as canonical run truth progresses through time.
This is not a violation of append-only artifact principles because a run record is a status projection, not an artifact payload.

But:
- history-sensitive changes should remain auditable where appropriate
- terminal truth must not be silently softened

## 6. Recommended Table Role

Run records are best understood as:
- product continuity rows
- query acceleration rows
- workspace/account history rows

They are not:
- canonical trace
- canonical artifact payloads
- ad hoc runtime control overrides

## 7. Product-facing Uses

Run records support:
- workspace run lists
- recent activity
- result lookup
- failure history
- account/workspace continuity
- future notifications or delivery tracking

## 8. What Must Never Happen

The following are forbidden:

1. run record status contradicting known canonical engine status
2. run records being used to infer execution semantics not present in engine truth
3. deleting lineage linkage to target/workspace/user
4. treating run records as full replacement for trace or result surfaces
5. client-side optimistic state being persisted as canonical run record truth

## 9. Final Statement

Run records in Nexa are product continuity projections of engine-originated run truth.

The server owns them.
The engine does not depend on them for meaning.

That distinction must remain explicit if Nexa is to scale without turning persistence into informal semantics.
