# Phase 4.5 Decision Record 04 — Secret and Provider Credential Management

## Recommended save path
`docs/specs/meta/phase45_decisions/04_secret_and_provider_credential_decision.md`

## 1. Purpose

This document records the recommended secret-management and provider-credential strategy for Phase 4.5.

Its purpose is to define where canonical managed-provider credentials live and how they stay separated from local/dev credentials.

## 2. Decision Status

- Status: `RECOMMENDED_FINAL_DRAFT`
- Gate area: `4.4 Secret / Provider Credential Management`
- Decision owner: `User + ChatGPT`
- Decision date: `2026-04-10`

## 3. Final Recommendation

- Selected option: `AWS Secrets Manager`

## 4. What This Means

AWS Secrets Manager becomes the canonical authority for server-side product credentials such as:

- managed provider API credentials
- service-to-service secrets
- outbound integration secrets
- environment-specific secure configuration

This decision also means:

- local/dev bridge credentials remain separate from product credentials
- local keys are not treated as canonical product authority
- secret access is controlled by server-side policy, not by UI convenience

## 5. Why This Is the Recommended Choice

### 5.1 Best fit with AWS-first direction

Once AWS-first hosting is chosen, AWS Secrets Manager becomes the cleanest and least fragmented secret authority.

### 5.2 Better than encrypted-DB-first for core secrets

Database storage can hold encrypted values, but the canonical root authority for secrets should not be the same as normal product persistence.

### 5.3 Keeps local bridge path clearly separate

Phase 4.5 requires a clear distinction between:
- local/dev bridge path
- canonical SaaS managed-provider path

Using AWS Secrets Manager makes that separation much easier to preserve.

### 5.4 Operationally simpler than rolling custom secret logic

A small team should not invent its own secret platform if a stable managed secret service already fits the stack.

## 6. Required Security Rules

Recommended rules:

- canonical managed-provider credentials live only in AWS Secrets Manager
- local/dev bridge credentials remain local and non-canonical
- the UI must never become the secret authority
- server-side access to secrets is role/policy-bounded
- secret rotation must be supported operationally
- workspace-scoped provider credentials may be supported later, but still through the same secret authority model

## 7. Access Boundary

Recommended access rule:

- only trusted server-side components may read canonical managed-provider secrets
- clients and browsers never receive raw managed-provider root credentials
- audits/logs must record secret usage events at a product-appropriate level without exposing secret values

## 8. Alternatives Considered

### 8.1 Encrypted DB-backed secret storage
Possible later for some workspace-scoped patterns, but not recommended as the primary secret authority.

### 8.2 Vault
Strong option, but too heavy for this project stage.

### 8.3 KMS-only custom design
Usable, but introduces more custom secret-management work than necessary.

## 9. PASS / FAIL Interpretation

This decision should be treated as `PASS` for Gate 4.4 if the project accepts:

`AWS Secrets Manager as the canonical secret authority`

If the project rejects that direction, Gate 4.4 remains `FAIL`.

## 10. Final Statement

Nexa should adopt AWS Secrets Manager as the canonical authority for Phase 4.5 server-side secrets and managed-provider credentials.

That is the best balance of:
- security
- platform coherence
- operational simplicity
- clean separation from local/dev bridge credentials
