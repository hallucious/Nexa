# Phase 4.5 Architecture Summary v1

## Recommended save path
`docs/specs/meta/phase45_decisions/phase45_architecture_summary.md`

## 1. Purpose

This document consolidates the six infrastructure decisions required for the Phase 4.5 implementation gate.

Its purpose is to turn separate decision records into one explicit architectural direction for Nexa's canonical SaaS + mobile product path.

This document is the final summary used to decide whether Phase 4.5 implementation may begin.

## 2. Plain-Language Meaning

This summary answers one simple question:

How should Nexa be built on the server side so that it can grow from the current local/product shell into a real web + mobile service without major foundation rework?

In plain language, the recommended answer is:

- use AWS as the main cloud/home for the product
- store product data in PostgreSQL
- use Clerk for login/session handling
- keep API keys and other secrets in AWS Secrets Manager
- expose product backend capabilities through a REST API
- treat the server as the official source of account/session/workspace/run continuity across web and mobile

## 3. Decision Summary Table

| Gate Area | Status | Chosen Direction | Ready for Implementation |
|----------|--------|------------------|--------------------------|
| 4.1 Hosting / Cloud | PASS | AWS-first managed cloud direction | YES |
| 4.2 Database | PASS | PostgreSQL (AWS-managed interpretation) | YES |
| 4.3 Authentication | PASS | Clerk | YES |
| 4.4 Secret / Provider Credential | PASS | AWS Secrets Manager | YES |
| 4.5 Server API Shape | PASS | REST + monorepo integrated backend + mixed sync/async jobs | YES |
| 4.6 Mobile/Web Session Continuity | PASS | Server-authoritative continuity with short-lived access tokens and refresh renewal | YES |

## 4. Consolidated Architecture Direction

### 4.1 Hosting

Canonical product direction:
- AWS-first managed cloud

Meaning:
- Nexa's real product backend lives in AWS-managed infrastructure
- local/dev bridge paths may still exist, but they are not the canonical product authority

### 4.2 Persistence

Canonical product database:
- PostgreSQL

Meaning:
- workspaces, runs, results, onboarding continuity, and account-linked product data live in PostgreSQL
- migration-based schema evolution is assumed from the beginning

### 4.3 Identity / Session

Canonical auth authority:
- Clerk

Meaning:
- Clerk owns sign-in/session identity flows
- Nexa maps authenticated users to product-specific workspace/run permissions and ownership

### 4.4 Provider Security / Credential Management

Canonical secret authority:
- AWS Secrets Manager

Meaning:
- managed provider credentials and other server-side secrets live there
- local/dev keys remain non-canonical and separate from product authority

### 4.5 API Shape

Canonical backend surface:
- REST API
- monorepo integrated backend
- mixed synchronous reads/writes plus asynchronous execution jobs

Meaning:
- simple product-facing operations can be sync
- long-running runs, retries, delivery, and later automation flows must use async/background job boundaries

### 4.6 Web / Mobile Continuity

Canonical continuity rule:
- server-authoritative product continuity

Meaning:
- web and mobile both rely on the same backend truth
- session continuity uses short-lived access tokens plus refresh renewal
- onboarding, workspace discovery, run/result history, and future first-success unlock continuity are server-owned product truth
- local `.nex.ui` state remains local convenience only

## 5. Explicit Boundary Statement

### 5.1 What may be designed now

The following are already allowed:

- detailed Phase 4.5 contracts/specs
- backend domain model design
- API route design
- database schema design
- auth integration design
- worker/job model design
- provider management design
- non-production architecture validation prototypes

### 5.2 What may be implemented now

Because all six gate areas are now explicitly decided in recommended-final form, the following may now begin:

- production-grade Phase 4.5 backend foundation work
- auth integration
- database-backed workspace registry
- run/result history persistence
- onboarding continuity persistence
- REST backend route implementation
- async/background execution infrastructure compatible with the chosen architecture
- secret/credential integration through AWS Secrets Manager

### 5.3 What remains blocked

Even after this summary, the following should still remain blocked until specifically designed at implementation level:

- random platform drift away from the six chosen decisions
- self-built auth experiments replacing Clerk
- alternative database/platform branching without explicit re-decision
- local `.nex.ui` being treated as canonical SaaS/mobile continuity
- ad hoc credential storage outside the chosen secret authority
- premature multi-service explosion without real scaling need

## 6. Why This Set Is the Recommended Combination

This exact combination is recommended because it gives the best balance for Nexa's current situation:

### 6.1 Easy enough to understand
It avoids overly exotic architecture.

### 6.2 Strong enough for future growth
It fits SaaS + mobile, background execution, and product continuity.

### 6.3 Low rework risk
The pieces fit together instead of fighting each other.

### 6.4 Good for a small team
It avoids self-building infrastructure that already has solid managed solutions.

## 7. Consistency Check

Confirm all of the following:

- AWS-first hosting is compatible with PostgreSQL persistence
- Clerk is compatible with web/mobile continuity
- AWS Secrets Manager is compatible with AWS-first hosting and managed-provider security
- REST + monorepo backend is compatible with mixed sync/async execution
- server-authoritative continuity is compatible with SaaS/mobile product direction
- local/dev bridge path remains clearly separated from canonical SaaS path

Status:
- [x] PASS
- [ ] FAIL

## 8. Gate Decision

Final gate result:
- [x] PASS — Phase 4.5 implementation may begin
- [ ] FAIL — only design/spec work may continue

## 9. Practical Meaning for a Non-Technical Reader

This does not mean “the product is finished.”

It means:

the foundation choices are now stable enough that real server-side product implementation can start without guessing the basics later.

In simpler words:

Before this document, the question was
“Where should we build this?”

After this document, the answer is
“We know where and how to build it, so implementation can start.”

## 10. Final Statement

Phase 4.5 now has a coherent recommended architecture set:

- AWS
- PostgreSQL
- Clerk
- AWS Secrets Manager
- REST
- server-authoritative web/mobile continuity

With these six decisions aligned, Phase 4.5 implementation may begin.
