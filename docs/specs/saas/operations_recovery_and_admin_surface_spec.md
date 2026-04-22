# Nexa Operations, Recovery, and Admin Surface Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Operational durability specification
Authority scope: Backup, restore, lifecycle, cleanup, admin/support actions, and incident handling
Recommended path: `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`

## 1. Purpose

This document defines how the Nexa SaaS remains operable after things go wrong.

Its purpose is to fix:
- backup expectations,
- restore direction,
- lifecycle and cleanup semantics,
- what operators can do,
- what they cannot do,
- and how support/admin capability becomes a product requirement rather than a pile of SQL queries.

## 2. Recovery principle

A production SaaS is not operationally real unless it can:
- back up,
- restore,
- diagnose,
- and support incidents through deliberate product surfaces.

## 3. Database backup baseline

The baseline SaaS requires:
- regular base backups,
- continuous or near-continuous WAL-style change durability where available,
- backup retention,
- encryption,
- and periodic restore verification.

Backups that are never restored in practice are not enough.
Verification is part of the requirement.

## 4. Restore rule

A restore workflow must:
1. restore the authoritative database,
2. bring migrations to the correct head,
3. validate basic product health,
4. then reconcile dependent runtime surfaces such as queue state.

Recovery must not guess backwards from non-authoritative systems.

## 5. Redis loss rule

Redis loss is survivable because Redis is not the business-state source of truth.

The SaaS must preserve enough durable submission and result state to reconstruct:
- which runs were accepted,
- which finished,
- which need re-enqueue or resubmission.

## 6. File-object lifecycle

The SaaS must define lifecycle treatment for:
- rejected uploads,
- expired uploads,
- orphaned objects,
- user-deleted objects,
- and retained objects associated with durable product history.

Object storage cannot be left to grow without policy.

## 7. Cleanup jobs

The SaaS must run scheduled cleanup jobs for short-lived or lifecycle-managed state such as:
- expired uploads,
- dedupe rows,
- old submission rows,
- quota windows,
- and archive-index generation.

Cleanup jobs must be:
- explicit,
- schedulable,
- observable,
- and documented.

## 8. Archival versus deletion

Archival is not deletion.

For immutable execution history, the SaaS must support:
- hiding archived records from default read surfaces,
- preserving auditability,
- and managing cost through indexing, storage tiering, or export strategies,

without mutating or deleting immutable execution rows.

## 9. Admin surface role

The admin surface exists so operators can:
- diagnose incidents,
- support customers,
- recover from runtime issues,
- and reconcile platform state

without directly writing ad hoc SQL against production.

## 10. Admin-surface boundaries

The admin surface is:
- internal-only,
- role-gated,
- auditable,
- and intentionally narrower than unrestricted database access.

It is not a backdoor that bypasses product governance.

## 11. Minimum admin capabilities

A conforming admin surface must support at least:

1. failed-run diagnosis,
2. stuck-job reprocessing,
3. upload quarantine review,
4. quota and subscription inspection,
5. provider health inspection,
6. webhook replay/reconciliation,
7. audit log visibility.

## 12. Operator action audit

Every operator/admin action that changes product state must be logged in immutable audit history.

This includes:
- retries,
- force resets,
- overrides,
- replay actions,
- plan adjustments,
- and quarantine overrides.

## 13. Runbooks

The SaaS must maintain runbooks for at least:
- database restore,
- Redis loss,
- S3 incident,
- stuck worker or stalled queue.

These runbooks are part of the product’s operational truth, not optional wiki decorations.

## 14. Permanent audit rule

Certain audit tables must remain permanent.
Support convenience or privacy workflow must not silently erase platform accountability.

## 15. Relationship to user deletion

User deletion does not mean all traces of platform history vanish.
The SaaS must distinguish:
- mutable user-owned state,
- deletable object state,
- and permanent operational audit.

## 16. Support without SQL principle

A mature SaaS should not require the default support loop to be:
- “open psql,
- write custom query,
- infer incident state by hand.”

That may still happen for debugging edge cases, but it is not the desired baseline.

## 17. Non-goals

This document does not define:
- a polished enterprise admin console,
- broad analytics warehouse governance,
- or full internal staffing/process policy.

It defines the product-level operational surfaces required to run Nexa responsibly.

## 18. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. database backup and restore expectations are explicit,
2. Redis-loss recovery is coherent with source-of-truth rules,
3. cleanup and lifecycle jobs are explicit and bounded,
4. immutable execution history is archived without mutation/deletion,
5. operators can diagnose and support incidents without raw SQL as the default path,
6. all meaningful admin mutations are audited,
7. and runbooks exist for the primary incident classes.
