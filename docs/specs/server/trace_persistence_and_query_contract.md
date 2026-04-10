# Trace Persistence and Query Contract v1

## Recommended save path
`docs/specs/server/trace_persistence_and_query_contract.md`

## 1. Purpose

This document defines how engine-originated trace truth is persisted, indexed, and queried through the server/product layer.

Its purpose is to preserve canonical trace meaning while still allowing product-facing observability, timeline inspection, and debugging surfaces.

## 2. Core Decision

Trace is engine-originated temporal truth.

Official rule:

- the engine emits canonical trace events
- the server may persist trace events, summaries, and indexes
- the server may expose trace query surfaces
- the server must not synthesize missing canonical events

## 3. Query Surfaces

Recommended endpoint families:

- `GET /api/runs/{run_id}/trace`
- later optional:
  - filtered trace queries
  - paginated event slices
  - summary endpoints

## 4. Trace Response Levels

Recommended levels:

### 4.1 Summary level
Compact product-facing timeline summary.

### 4.2 Event level
Ordered canonical trace events.

### 4.3 Deep payload level
Optional retrieval of detailed event payloads where policy allows.

## 5. Recommended Summary Response Shape

    {
      "run_id": "run_001",
      "status": "running",
      "latest_event_time": "2026-04-10T12:00:25Z",
      "event_count": 37,
      "current_focus": {
        "node_id": "review_bundle",
        "label": "Review Bundle"
      }
    }

## 6. Recommended Event Query Shape

    {
      "run_id": "run_001",
      "events": [
        {
          "event_id": "evt_001",
          "sequence": 1,
          "event_type": "run_started",
          "severity": "info",
          "node_id": null,
          "timestamp": "2026-04-10T12:00:02Z",
          "message": "Run started."
        }
      ],
      "next_cursor": null
    }

## 7. Persistence Model

Recommended rule:

- PostgreSQL may store summary/index rows and searchable event metadata
- larger trace payloads may be split into efficient event storage strategies if needed
- the chosen persistence shape must preserve canonical ordering and event identity

Minimum preserved trace properties:
- run linkage
- ordering
- timestamp
- event type
- severity where relevant
- node/resource linkage where relevant

## 8. Ordering Rule

Trace query must preserve canonical event order.

The server may paginate.
It may not reorder meaningfully ordered canonical events.

## 9. Summary Rule

The server may compute summary views such as:
- event counts
- latest signal
- active node summary
- failure summary

But:
- summaries must remain traceable to canonical event truth
- summaries must not replace canonical events

## 10. Authorization Rule

Trace access is product-layer authorized.

Recommended rule:
- the caller must be authorized for the parent workspace/run scope
- trace ids/events alone are not sufficient proof of access

## 11. What Must Never Happen

The following are forbidden:

1. inventing missing canonical events
2. reordering canonical event timelines
3. flattening important engine failures into vague product-only language without preserving canonical event meaning
4. mixing local UI continuity events into canonical server trace
5. using summary view as if it were the full canonical trace

## 12. Final Statement

Trace in Nexa is engine-originated temporal truth.

The server may persist, index, and query it.
It may not invent it.

That rule must remain explicit if Nexa observability is to stay trustworthy.
