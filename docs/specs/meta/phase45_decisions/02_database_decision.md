# Phase 4.5 Decision Record 02 — Database Choice

## Recommended save path
`docs/specs/meta/phase45_decisions/02_database_decision.md`

## 1. Purpose

This document records the recommended primary database choice for Phase 4.5.

Its purpose is to define where Nexa's canonical product continuity data will live.

## 2. Decision Status

- Status: `RECOMMENDED_FINAL_DRAFT`
- Gate area: `4.2 Database Choice`
- Decision owner: `User + ChatGPT`
- Decision date: `2026-04-10`

## 3. Final Recommendation

- Selected option: `PostgreSQL`
- Recommended deployment interpretation: `AWS-managed PostgreSQL`

## 4. What This Means

PostgreSQL becomes the canonical database family for:

- workspace registry
- run history
- result history
- onboarding continuity state
- user/account/workspace relationships
- future quota/accounting linkage
- JSON-heavy metadata storage where needed

## 5. Why This Is the Recommended Choice

### 5.1 Best general-purpose fit

Nexa needs one database that can handle:
- relational identity/workspace data
- structured history tables
- queryable run/result records
- some JSON-heavy payloads

PostgreSQL is the most balanced choice for that mix.

### 5.2 Lowest complexity-risk ratio

This project does not need clever database specialization first.
It needs one stable, boring, widely supported foundation that reduces architectural risk.

### 5.3 Strong compatibility with AWS-first direction

PostgreSQL fits cleanly with the AWS-first recommendation and does not force a new platform split.

### 5.4 Better default than over-specialized alternatives

PlanetScale-like MySQL-first direction is less attractive because Nexa is likely to benefit from PostgreSQL’s general flexibility and JSON support.
Supabase is useful, but as a product bundle it mixes DB and auth/platform decisions too early.
The database family choice should stay simpler here.

## 6. Required Fit Areas

This PostgreSQL choice is intended to support:

- workspace registry
- run history
- result history
- onboarding continuity
- account/quota linkage
- structured metadata tables
- migration-safe long-term persistence

## 7. Migration Direction

Recommended rule:

- use ordinary migration tooling from the beginning
- treat schema changes as explicit product decisions
- do not rely on ad hoc manual database mutation

## 8. Alternatives Considered

### 8.1 Supabase
Useful bundle, but it collapses several later decisions together too early.

### 8.2 PlanetScale / MySQL-first
Not the strongest fit for Nexa’s likely JSON-heavy and product-continuity-heavy needs.

### 8.3 SQLite-first canonical product DB
Acceptable only for local tooling, not for the canonical SaaS/mobile path.

## 9. PASS / FAIL Interpretation

This decision should be treated as `PASS` for Gate 4.2 if the project accepts:

`PostgreSQL as the canonical database family`

If the project rejects that direction, Gate 4.2 remains `FAIL`.

## 10. Final Statement

Nexa should adopt PostgreSQL as the canonical database family for Phase 4.5 and interpret it through AWS-managed PostgreSQL deployment.

That is the best balance of:
- reliability
- flexibility
- migration safety
- future product continuity support
