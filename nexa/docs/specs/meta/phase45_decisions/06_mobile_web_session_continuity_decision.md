# Phase 4.5 Decision Record 06 — Mobile and Web Session Continuity

## Recommended save path
`docs/specs/meta/phase45_decisions/06_mobile_web_session_continuity_decision.md`

## 1. Purpose

This document records the recommended mobile/web session continuity model for Phase 4.5.

Its purpose is to define how Nexa preserves user continuity across web and mobile clients without confusing local UI continuity with canonical product continuity.

## 2. Decision Status

- Status: `RECOMMENDED_FINAL_DRAFT`
- Gate area: `4.6 Mobile / Web Session Continuity`
- Decision owner: `User + ChatGPT`
- Decision date: `2026-04-10`

## 3. Final Recommendation

- Selected model: `server-authoritative continuity with short-lived access tokens + refresh-based session renewal`

## 4. What This Means

This decision means:

- web and mobile both rely on the same canonical backend continuity
- authenticated identity/session continuity is server-authoritative
- short-lived access tokens are used for active requests
- refresh-based renewal preserves sign-in continuity across sessions/devices
- onboarding state, first-success unlock state, workspace discovery, and run/result continuity live on the server as canonical product truth
- local `.nex.ui` continuity remains local convenience only, not canonical product truth

## 5. Why This Is the Recommended Choice

### 5.1 Clean separation between local convenience and product truth

This project already distinguishes UI continuity from canonical truth.
That same discipline must carry into web/mobile continuity.

### 5.2 Best fit for cross-device use

If a user starts on web and continues on mobile, the system should recover:
- account identity
- owned workspaces
- onboarding progress
- return-use history
- recent results

That requires server-authoritative continuity.

### 5.3 Safer than long-lived client-authoritative sessions

Short-lived access tokens with refresh-based renewal are the more responsible default than loose long-lived client tokens.

### 5.4 Supports future SaaS behavior cleanly

This decision prepares for:
- mobile app continuity
- multi-device reuse
- account-based libraries/history
- future collaboration-ready product flows

## 6. Required Continuity Rules

Recommended rules:

- identity continuity is auth-authority based
- session continuity is refresh-renewed
- onboarding/unlock continuity is stored server-side
- workspace registry is server-side canonical truth
- run/result history is server-side canonical truth
- local `.nex.ui` state may restore editor comfort, but must never masquerade as canonical product continuity

## 7. Offline Rule

Recommended early rule:

- no strong offline-first promise for canonical product continuity
- local UI continuity may still restore local editing comfort when available
- canonical product state is recovered from the server when authenticated connectivity returns

## 8. Alternatives Considered

### 8.1 Local-first continuity as canonical truth
Rejected.
Conflicts with SaaS/mobile continuity goals.

### 8.2 Long-lived client-only token model
Rejected.
Too weak as a security/control default.

### 8.3 Device-specific disconnected session semantics
Rejected.
Too likely to fragment the user experience and product truth.

## 9. PASS / FAIL Interpretation

This decision should be treated as `PASS` for Gate 4.6 if the project accepts:

`server-authoritative continuity with short-lived access tokens and refresh-based renewal`

If the project rejects that direction, Gate 4.6 remains `FAIL`.

## 10. Final Statement

Nexa should adopt a server-authoritative web/mobile continuity model with:

- short-lived access tokens
- refresh-based session renewal
- server-owned onboarding/workspace/run/result continuity
- local `.nex.ui` preserved only as local UI convenience

That is the best balance of:
- product clarity
- security
- cross-device continuity
- avoiding confusion between UI state and canonical product truth
