# Phase 4.5 Decision Record 01 — Hosting and Cloud Direction

## Recommended save path
`docs/specs/meta/phase45_decisions/01_hosting_cloud_decision.md`

## 1. Purpose

This document records the recommended hosting/cloud direction for Phase 4.5.

Its purpose is to remove platform ambiguity before production-grade Phase 4.5 implementation begins.

## 2. Decision Status

- Status: `RECOMMENDED_FINAL_DRAFT`
- Gate area: `4.1 Hosting / Cloud Direction`
- Decision owner: `User + ChatGPT`
- Decision date: `2026-04-10`

## 3. Final Recommendation

- Selected option: `AWS-first managed cloud direction`

## 4. What This Means

The canonical product path for Nexa will assume:

- AWS is the primary hosting/cloud authority
- the shared backend for web and mobile lives in AWS-managed infrastructure
- background execution is supported as a first-class capability
- persistence, secret handling, and future managed-provider operations are designed for that AWS-first path
- local/dev bridge paths may continue to exist, but they are not the canonical product authority

## 5. Why This Is the Recommended Choice

### 5.1 Best fit for Nexa's next phase

Nexa is moving from first-success loop work into a SaaS/mobile-capable server foundation.
That favors a cloud-first authority over local-first or self-hosted-first direction.

### 5.2 Strong fit for async execution

Nexa is not only a request/response product.
It needs run launch, background work, run/result history, observability linkage, and future managed-provider operations.
That makes a background-job-friendly cloud direction the rational default.

### 5.3 Lowest future rework risk

AWS provides a reliable long-run ceiling for:
- API hosting
- workers/background jobs
- secret management
- queue/event patterns
- managed persistence
- mobile-ready backend foundations

### 5.4 Still compatible with efficiency

This decision does not mean “build everything from low-level AWS primitives immediately.”

The intended interpretation is:
- choose AWS as the canonical direction
- use managed services as much as possible
- avoid premature operational complexity
- keep the earliest implementation small, but aligned with the long-term product path

## 6. Scope Covered by This Decision

This decision covers the assumed direction for:

- web API hosting
- background job hosting
- persistent storage environment
- future mobile support
- secret-management hosting context
- dev/staging/production environment separation direction

## 7. Staging / Production Rule

Recommended rule:

- separate development and production from the start of production-grade Phase 4.5 work
- staging may be deferred only temporarily during very early implementation
- if staging is deferred, that decision must be recorded explicitly and revisited before external-user rollout

## 8. Alternatives Considered

### 8.1 GCP
Strong platform, but no project-specific reason to prefer it over AWS right now.

### 8.2 Azure
Strong enterprise platform, but currently offers no clearer fit than AWS for Nexa’s immediate path.

### 8.3 Self-hosted-first
Too much operational burden for too little advantage at this stage.

### 8.4 Hybrid-first
Creates too much ambiguity too early and risks decision drift.

## 9. PASS / FAIL Interpretation

This decision should be treated as `PASS` for Gate 4.1 if the project accepts:

`AWS-first managed cloud direction`

If the project rejects that direction, Gate 4.1 is still `FAIL`.

## 10. Final Statement

Nexa should adopt an AWS-first managed cloud direction for the canonical Phase 4.5 product path.

That is the best balance of:
- long-term scalability
- async execution fit
- SaaS/mobile alignment
- manageable implementation risk
