# Async Execution and Worker Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/async_execution_and_worker_implementation_plan.md`

## 1. Purpose

This plan implements the transition from synchronous request-bound execution to queue-backed asynchronous execution.

Its primary outcome is that run submission returns quickly, workers process jobs independently, and run state remains recoverable across worker or Redis incidents.

## 2. Governing spec references

- `docs/specs/saas/async_execution_and_run_state_spec.md`
- `docs/specs/saas/saas_foundation_and_governance_spec.md`
- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`

## 3. Goals

1. `POST /api/runs` becomes non-blocking.
2. A submitted run is durable before queue enqueue.
3. Worker execution updates authoritative state safely.
4. Redis loss is survivable through Postgres-backed submission recovery.
5. Admin run retry/reset actions map cleanly onto queued execution.

## 4. Core implementation decisions

- Queue backend: Redis + arq
- Authoritative submission durability: Postgres `run_submissions`
- Authoritative final result: Postgres `execution_record`
- Queue state is operational, not business-authoritative
- Worker orchestration consumes existing queue domain models where possible

## 5. Work packages

### Package A1 — Queue runtime bootstrap

Required outcomes:
- Redis client creation
- arq worker settings
- worker start script
- queue job naming and timeout policy
- max worker concurrency config

Expected files:
- `src/server/queue/redis_client.py`
- `src/server/queue/worker_settings.py`
- `scripts/start_worker.py`

### Package A2 — Durable run submission record

Required outcomes:
- `run_submissions` row inserted before enqueue
- clear submission statuses
- TTL/expiry strategy
- retry-safe semantics when enqueue partially fails

Expected files:
- `src/server/pg/run_submission_store_pg.py`
- migration creating `run_submissions`
- admission flow integration

### Package A3 — Run launcher and bridge integration

Required outcomes:
- `run_engine_async` no longer performs direct execution for normal SaaS run path
- enqueue returns accepted/queued response
- worker executes the actual engine path
- launch response and polling semantics updated consistently

Expected files:
- `src/server/queue/run_launcher.py`
- `src/server/engine_bridge.py`
- `src/server/run_admission.py`

### Package A4 — Worker execution path

Required outcomes:
- worker reconstructs execution target safely
- worker writes terminal result into `execution_record`
- worker updates submission status
- worker emits lifecycle logs and notifications
- worker integrates with recovery policy hooks

Expected files:
- `src/server/queue/worker_functions.py`
- execution record store integration
- action log integration

### Package A5 — Status reconciliation

Required outcomes:
- poll endpoint maps queue state and final record state coherently
- transient queue states are visible
- terminal state prefers `execution_record`
- inconsistent states produce deterministic fallback classification

### Package A6 — Recovery and orphan handling

Required outcomes:
- reprocess orphan logic
- Redis loss reconciliation using `run_submissions`
- admin-triggered retry/requeue path
- cleanup of expired submission rows

Expected files:
- `src/server/queue/cleanup_jobs.py`
- `src/server/run_control_api.py`
- admin recovery integration

## 6. Data model requirements

The following state classes must be explicit:

- submission accepted but not enqueued
- queued
- claimed by worker
- running
- completed
- failed
- requeued
- lost_redis
- cancelled if cancellation is later introduced

Transitions must be deterministic and auditable.

## 7. Test requirements

Minimum tests:

1. enqueue returns quickly and does not block on engine completion
2. worker completes a real queued run
3. final result is visible through polling and result endpoints
4. Redis loss recovery reconciles against `run_submissions`
5. orphan reprocessing works
6. run submission TTL cleanup only deletes terminal/expired rows
7. existing synchronous baseline tests do not regress unexpectedly

## 8. Exit criteria

This segment is complete only if:

1. the product is no longer dependent on request-bound sync execution,
2. a run survives transient queue loss through submission durability,
3. worker and API surfaces agree on run state,
4. admin recovery actions are possible without direct DB surgery,
5. tests prove end-to-end queued execution behavior.
