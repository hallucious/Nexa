# Database Append-Only and Lineage Persistence Contract v1

## Recommended save path
`docs/specs/server/database_append_only_lineage_persistence_contract.md`

## 1. Purpose

This document defines the database-level persistence rules needed to preserve Nexa's architectural commitments around append-only outputs and lineage-aware history.

Its purpose is to make sure PostgreSQL schema design supports Nexa truth instead of accidentally corrupting it.

## 2. Core Decision

The database is a persistence/query layer, not a semantic authority.

Official rule:

- PostgreSQL stores canonical references, continuity records, indexes, and approved product projections
- PostgreSQL schema must preserve append-only and lineage rules where those rules apply
- PostgreSQL must not become the place where execution meaning is casually rewritten

## 3. Scope

This contract applies to persistence rules for:

- artifact rows / artifact references
- trace-related rows / indexes
- run records
- lineage relationships
- history-sensitive product projections

## 4. Append-Only Rule Families

### 4.1 Canonical artifact meaning
Artifact meaning must never be overwritten in place.

Recommended DB interpretation:
- new semantic output → new artifact identity
- preview/update caches may change outside canonical artifact meaning
- canonical artifact rows should be treated as immutable in meaning after creation

### 4.2 Trace events
Canonical event rows should preserve identity/order/meaning.
Do not overwrite event meaning in place.

### 4.3 History-sensitive lineage
Lineage relationships should be inserted/extended, not casually rewritten in ways that destroy historical traceability.

## 5. Lineage Rule

The database should preserve queryable lineage between:

- workspace
- target save/snapshot
- run
- artifact
- trace
- optional downstream delivery/evaluation records where designed

This allows users and server APIs to answer:
- where did this result come from?
- which run produced this artifact?
- which target did this run execute?
- what history chain led here?

## 6. Recommended Schema Interpretation

Recommended categories of tables/rows:

### 6.1 Mutable projection tables
Examples:
- workspace metadata
- run current-known status projection
- onboarding continuity

These may update over time.

### 6.2 Immutable/append-oriented tables
Examples:
- artifact records
- trace event records
- lineage relation records where historical preservation is required

These should prefer insert/append semantics.

## 7. Query Optimization Rule

Indexes, materialized summaries, and denormalized query helpers are allowed.

But:
- optimization layers must not become the hidden source of truth
- if summary and canonical rows disagree, canonical rows win

## 8. Migration and Versioning Rule

Recommended rule:

- use explicit DB migrations from the beginning
- migration history must remain auditable
- DB schema evolution must be reviewed as part of Phase 4.5 contract-aware implementation
- DB version drift must not silently break spec-version sync discipline

Recommended initial migration direction:
- Alembic-compatible migration flow

## 9. What Must Never Happen

The following are forbidden:

1. overwriting canonical artifact meaning in place
2. rewriting trace event meaning in place
3. deleting lineage links in a way that breaks historical explainability without explicit retention policy
4. using mutable projection tables as if they were canonical engine history
5. allowing DB convenience to redefine append-only architectural rules

## 10. Final Statement

PostgreSQL in Nexa is the persistence and query backbone for product continuity.

It must support append-only and lineage-aware truth.
It must not erase them.

That rule must remain explicit if Nexa is to scale without losing architectural trustworthiness.
