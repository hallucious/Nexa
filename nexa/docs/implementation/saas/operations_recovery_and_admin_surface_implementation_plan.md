# Operations, Recovery, and Admin Surface Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/operations_recovery_and_admin_surface_implementation_plan.md`

## 1. Purpose

This plan implements the operational durability and operator-support layer of the SaaS system.

It covers:
- backup,
- restore verification,
- cleanup jobs,
- execution archival visibility,
- incident runbooks,
- internal admin/support APIs.

## 2. Governing references

- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`
- `docs/specs/saas/saas_foundation_and_governance_spec.md`
- `docs/specs/saas/observability_security_and_privacy_spec.md`

## 3. Goals

1. Make backup and restore real runtime responsibilities.
2. Make cleanup and retention flows explicit and scheduled.
3. Keep archival visibility compliant with immutable-record rules.
4. Let operators handle common incidents without raw SQL.
5. Keep all operator actions auditable.

## 4. Core implementation decisions

- Postgres backup is first-class operational work,
- Redis loss is recoverable through authoritative Postgres state,
- S3 lifecycle is policy-driven,
- execution archival is index-driven and read-surface-driven,
- admin tooling is internal-only and role-gated,
- audit surfaces remain immutable/permanent where specified.

## 5. Work packages

### Package R1 — Backup and restore discipline
Outcomes:
- backup destination and retention configured,
- restore runbook exists,
- restore verification job exists,
- restore drill cadence defined.

### Package R2 — Cleanup and lifecycle jobs
Outcomes:
- expired uploads cleaned,
- orphaned uploads cleaned,
- dedupe rows cleaned,
- run-submission TTL cleanup works,
- quota lifecycle cleanup works,
- archive-index insertion job works.

### Package R3 — Redis loss and queue recovery
Outcomes:
- `run_submissions` is durable submission truth,
- reconciliation flow exists,
- operator can identify unrecovered submissions,
- requeue/notify behavior is deterministic.

### Package R4 — Execution archival visibility
Outcomes:
- archive index exists,
- default reads exclude archived runs where appropriate,
- admin reads can include them,
- immutable execution rows are untouched.

### Package R5 — Internal admin surface
Outcomes:
- failed run diagnosis works,
- stuck-job retry/reset works,
- upload review works,
- quota/subscription inspection works,
- provider health inspection works,
- webhook replay works.

### Package R6 — Audit integration
Outcomes:
- admin mutations logged,
- archival events logged,
- deletion events logged,
- audit views can be queried coherently.

## 6. Required runtime surfaces

- cleanup job runtime
- run submission store
- execution archive store
- admin API
- admin audit store
- docs/ops runbooks
- queue recovery logic

## 7. Operator safety requirements

The implementation must ensure:
- dangerous actions remain role-gated,
- reasons are captured for sensitive overrides,
- higher-friction checks exist where required,
- operator convenience never bypasses audit.

## 8. Completion criteria

This plan is complete only if:
1. backup jobs run and restore verification is defined,
2. cleanup jobs are real runtime jobs,
3. Redis-loss recovery uses defined durable surfaces,
4. archival affects visibility without mutating execution records,
5. operators can handle key incident classes without SQL,
6. all operator actions are auditable.
