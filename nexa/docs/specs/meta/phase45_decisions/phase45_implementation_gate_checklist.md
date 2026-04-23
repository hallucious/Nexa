# Phase 4.5 Implementation Gate Checklist v1

## Recommended save path
`docs/specs/meta/phase45_decisions/phase45_implementation_gate_checklist.md`

## 1. Purpose

This document defines the formal implementation gate that must be cleared before production-grade Phase 4.5 work begins.

Its purpose is to prevent premature server-side implementation from starting before the infrastructure architecture is decided clearly enough to avoid large rework.

This checklist exists because the updated implementation order v2.2 explicitly states:

- Phase 4.5 design/contract work may begin before the gate
- production-grade Phase 4.5 implementation must not begin before the gate

In short:

Design may begin now.
Production implementation may not begin yet unless this gate is passed.

## 2. Scope

This checklist applies only to Phase 4.5 production-grade implementation work.

In scope:
- auth/session implementation
- workspace registry implementation
- run/result history services
- onboarding continuity persistence
- managed provider foundation
- web/mobile shared API implementation
- secret/credential handling implementation
- database-backed product continuity infrastructure

Out of scope:
- high-level architecture discussion
- document/spec drafting
- API shape proposals
- hosting/auth/database option comparison
- non-production prototypes used only for architecture validation

Those may proceed before the gate.

## 3. Core Rule

Phase 4.5 implementation may start only when all 6 infrastructure decisions are explicitly made and recorded.

Required decisions:

1. hosting/cloud direction
2. database choice
3. authentication strategy
4. secret/provider credential management strategy
5. server API deployment shape
6. mobile/web session continuity approach

## 4. Gate Checklist

### 4.1 Hosting / Cloud Direction
Status: [ ] PASS  [ ] FAIL

Must be decided:
- AWS / GCP / Azure / self-hosted / hybrid / other

Must be recorded:
- chosen provider/platform
- deployment rationale
- expected hosting model for:
  - web API
  - background jobs
  - persistent storage
  - future mobile support
- whether staging/production separation is planned now or deferred

Fail if:
- “we will decide later” is still the real answer
- web and mobile assumptions imply different backend hosting shapes with no resolution
- managed-provider/server persistence assumptions exist without a hosting direction

### 4.2 Database Choice
Status: [ ] PASS  [ ] FAIL

Must be decided:
- PostgreSQL / Supabase / PlanetScale / managed SQL / other

Must be recorded:
- primary product database
- why it fits:
  - workspace registry
  - run history
  - result history
  - onboarding state
  - quota/accounting linkage
- migration strategy assumptions
- whether structured JSON-heavy storage is expected

Fail if:
- database is still only a vague placeholder
- chosen DB does not obviously support the required product continuity model
- identity/session/onboarding/run history assumptions depend on a DB not yet chosen

### 4.3 Authentication Strategy
Status: [ ] PASS  [ ] FAIL

Must be decided:
- self-built auth / Auth0 / Clerk / Supabase Auth / other

Must be recorded:
- identity owner
- session issuance model
- refresh/session renewal assumptions
- workspace ownership binding model
- guest/anonymous policy

Fail if:
- user identity is still conceptually assumed but auth is not chosen
- mobile/web session assumptions exist without an auth authority
- workspace ownership is still ambiguous

### 4.4 Secret / Provider Credential Management
Status: [ ] PASS  [ ] FAIL

Must be decided:
- Vault / AWS Secrets Manager / KMS / encrypted DB-backed storage / other

Must be recorded:
- where managed-provider credentials live
- who can access them
- how provider credentials are rotated
- whether workspace-scoped provider access is supported
- how local/dev bridge credentials differ from canonical product credentials

Fail if:
- managed provider is planned but no secret authority exists
- local/dev and product credentials are not clearly separated
- security/compliance assumptions depend on a secret layer not chosen yet

### 4.5 Server API Deployment Shape
Status: [ ] PASS  [ ] FAIL

Must be decided:
- REST / GraphQL / tRPC / mixed
- monorepo integrated backend vs separate service
- synchronous vs async/background job boundaries

Must be recorded:
- canonical API style
- primary service boundary
- run launch/status/result route shape
- workspace read/write route shape
- onboarding continuity route shape
- provider/accounting route shape

Fail if:
- web/mobile shared API is assumed but no concrete API shape exists
- run/result/workspace continuity surfaces are still only conceptual
- background execution requirements are implied but not reflected in API/service shape

### 4.6 Mobile / Web Session Continuity Approach
Status: [ ] PASS  [ ] FAIL

Must be decided:
- token/session model
- login persistence model
- cross-device continuity model
- onboarding/unlock continuity authority

Must be recorded:
- how web and mobile share user/session identity
- how first-success/unlock continuity is synchronized
- what is local UI continuity only
- what is canonical server continuity
- offline behavior policy, if any

Fail if:
- mobile/web are expected to share product continuity but no session continuity design exists
- local `.nex.ui` continuity is still implicitly treated as canonical product continuity
- unlock/onboarding state ownership is still ambiguous

## 5. Required Output Before Gate Pass

Before the gate can be marked PASS, all of the following must exist:

- one written architecture decision for each of the 6 gate areas
- one consolidated Phase 4.5 architecture summary
- one explicit statement of:
  - what may be designed now
  - what may be implemented now
  - what is blocked until after the gate

## 6. Gate Decision Rule

Phase 4.5 implementation is allowed only if:

- sections 4.1 through 4.6 are all PASS
- no section is “partially decided but good enough”
- the chosen decisions are consistent with the updated v2.2 implementation order
- local bridge path and canonical SaaS path remain clearly separated

If any one section fails:
- Phase 4.5 production implementation is blocked
- only design/spec work may continue

## 7. Immediate Next Work After This Checklist

Do this next:

1. create one decision record for each of the 6 gate areas
2. consolidate them into one Phase 4.5 architecture summary
3. only then decide whether the gate is passed

## 8. Final Statement

This checklist is not a planning nicety.

It is a hard boundary.

Without this gate, Phase 4.5 implementation risks building server/product foundations on assumptions that may later force major rework.
