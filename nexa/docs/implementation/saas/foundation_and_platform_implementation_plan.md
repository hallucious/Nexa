# Foundation and Platform Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/foundation_and_platform_implementation_plan.md`

## 1. Purpose

This plan defines the shared platform work that all other SaaS sectors depend on.

It exists to stop downstream sectors from repeatedly inventing their own answers to questions such as:
- where shared code should live,
- how new tables should be introduced,
- how env vars should be documented,
- how startup validation should work,
- how shared test harnesses should be structured,
- how cross-sector governance rules should be enforced.

## 2. Governing references

- `docs/specs/saas/saas_foundation_and_governance_spec.md`
- `docs/specs/saas/observability_security_and_privacy_spec.md`
- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`

## 3. Goals

1. Create a stable implementation substrate for all SaaS sectors.
2. Keep migration, schema, and environment changes disciplined.
3. Preserve table classification, PII placement, and source-of-truth rules in implementation.
4. Reduce duplication across later sector work.
5. Make the repository easier for a future AI or human to understand quickly.

## 4. Core implementation decisions

- Alembic remains the only migration authority.
- Postgres is the authoritative business-state store.
- Redis is operational, not business-authoritative.
- Shared runtime bootstrap happens in one predictable path.
- Immutable table rules must be reflected in both code and review discipline.
- New env vars are introduced in grouped families, not ad hoc.

## 5. Work packages

### Package F1 — Repository layout normalization
Required outcomes:
- a predictable `docs/specs` and `docs/implementation` pairing,
- stable shared-code placement for cross-sector runtime helpers,
- file names that express domain meaning rather than temporary patch intent.

### Package F2 — Migration and schema discipline
Required outcomes:
- every new runtime table appears in schema inventory,
- every table addition has a matching Alembic revision,
- no runtime path depends on a table missing from migration history.

### Package F3 — Environment variable governance
Required outcomes:
- `.env.example` remains grouped by concern,
- required versus optional vars are obvious,
- production-only secrets are clearly distinguishable from local-dev defaults.

### Package F4 — Shared startup and runtime bootstrap
Required outcomes:
- startup validation remains centralized,
- migration-head checks remain fail-fast,
- observability bootstrap is predictable,
- redaction hooks initialize before request handling and worker execution.

### Package F5 — Shared test harness
Required outcomes:
- sector-level integration tests can rely on stable test infrastructure,
- Postgres/Redis/object-storage style local test support is predictable,
- append-only and redaction checks can be reused across sectors.

## 6. Cross-sector governance rules

### 6.1 Mutability rule
If a table is immutable in the specs, no sector may add:
- update flows,
- soft-delete flags,
- anonymize-in-place flows,
- convenience cleanup deletes.

### 6.2 PII placement rule
Immutable tables must not store directly mutable identity fields.
If a sector needs directly identifying data, it must live in mutable/reference layers.

### 6.3 Source-of-truth rule
A cache or mirror must never silently become authoritative just because it is easier to use.

### 6.4 Inventory rule
If a runtime component exists, it must appear in the relevant inventories.

## 7. Completion criteria

This plan is complete only if:
1. downstream plans can rely on stable migration and env discipline,
2. shared startup and test conventions are established,
3. immutable-table and PII-placement rules are enforceable in practice,
4. future sector work can follow a clear repository structure without guessing.
