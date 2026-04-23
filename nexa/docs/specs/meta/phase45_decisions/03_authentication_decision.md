# Phase 4.5 Decision Record 03 — Authentication Strategy

## Recommended save path
`docs/specs/meta/phase45_decisions/03_authentication_decision.md`

## 1. Purpose

This document records the recommended authentication strategy for Phase 4.5.

Its purpose is to define who owns user identity and session lifecycle for the canonical product path.

## 2. Decision Status

- Status: `RECOMMENDED_FINAL_DRAFT`
- Gate area: `4.3 Authentication Strategy`
- Decision owner: `User + ChatGPT`
- Decision date: `2026-04-10`

## 3. Final Recommendation

- Selected option: `Clerk as external auth authority`

## 4. What This Means

Clerk becomes the recommended identity/session authority for:

- sign-in/sign-up
- session issuance
- refresh/session continuity
- web/mobile identity consistency
- user identity binding to Nexa workspaces

Nexa still owns:
- workspace semantics
- reviewer/owner authority semantics
- run launch context
- product-specific permissions

## 5. Why This Is the Recommended Choice

### 5.1 Best speed-to-correctness tradeoff

Authentication is full of costly failure modes.
For a small team and a non-specialist product owner, self-building auth is the wrong default.

### 5.2 Better practical fit than Cognito for this project stage

Cognito can work, but it is more complex to operate well and easier to misconfigure.
For this project stage, Clerk is the more practical recommendation.

### 5.3 Strong mobile/web continuity fit

Phase 4.5 explicitly cares about mobile/web continuity.
That favors an auth authority that already handles cross-platform identity/session flows cleanly.

### 5.4 Keeps Nexa focused on product-specific logic

Nexa should spend its design energy on:
- execution engine productization
- workspace continuity
- run/result history
- managed provider operations

It should not spend early Phase 4.5 effort reinventing login/session infrastructure.

## 6. Required Identity Rules

Recommended rules:

- Clerk is the identity authority
- Nexa stores Clerk user identity references in its own product database
- workspace ownership is bound to authenticated Nexa user records
- anonymous/guest mode is allowed only for limited local or demo surfaces, not for canonical long-term product continuity
- authenticated context is required for canonical server-side persistence

## 7. Session Model Direction

Recommended direction:

- short-lived access tokens
- renewable session continuity through Clerk-managed flows
- product backend trusts authenticated identity from Clerk and applies Nexa-specific authorization rules

## 8. Alternatives Considered

### 8.1 Self-built auth
Rejected.
Too much risk, too little value.

### 8.2 Auth0
Strong option, but less attractive here than Clerk for practical setup and developer ergonomics.

### 8.3 AWS Cognito
Acceptable in theory, but not the best recommendation for this project stage.

### 8.4 Supabase Auth
Useful if Supabase were the primary platform bundle, but that is not the recommended overall direction.

## 9. PASS / FAIL Interpretation

This decision should be treated as `PASS` for Gate 4.3 if the project accepts:

`Clerk as the canonical auth authority`

If the project rejects that direction, Gate 4.3 remains `FAIL`.

## 10. Final Statement

Nexa should adopt Clerk as the authentication authority for Phase 4.5.

That is the best balance of:
- speed
- safety
- cross-device continuity
- avoiding self-inflicted auth complexity
