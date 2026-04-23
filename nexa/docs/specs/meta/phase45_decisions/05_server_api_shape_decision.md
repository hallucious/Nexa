# Phase 4.5 Decision Record 05 — Server API Deployment Shape

## Recommended save path
`docs/specs/meta/phase45_decisions/05_server_api_shape_decision.md`

## 1. Purpose

This document records the recommended server API deployment shape for Phase 4.5.

Its purpose is to define how Nexa exposes canonical backend capabilities to web and mobile clients.

## 2. Decision Status

- Status: `RECOMMENDED_FINAL_DRAFT`
- Gate area: `4.5 Server API Deployment Shape`
- Decision owner: `User + ChatGPT`
- Decision date: `2026-04-10`

## 3. Final Recommendation

- Selected API style: `REST`
- Service boundary: `monorepo integrated backend`
- Execution boundary: `mixed sync + async/background job model`

## 4. What This Means

The recommended shape is:

- a monorepo-integrated backend service
- REST endpoints for product-facing API surfaces
- synchronous request/response only for lightweight operations
- async/background job flow for run execution, retries, delivery, and other long-running work

## 5. Why This Is the Recommended Choice

### 5.1 Best fit for a small team

REST is the most predictable and lowest-friction choice for:
- frontend integration
- mobile integration
- debugging
- documentation
- gradual product growth

### 5.2 Better first choice than GraphQL or tRPC here

GraphQL adds schema/query complexity that the project does not need first.
tRPC is attractive for some stacks, but less ideal as a long-term public-facing cross-client API contract.

### 5.3 Nexa needs async execution as a first-class boundary

Run launch, result generation, retries, delivery, and future automation are not naturally request/response-only problems.
So the backend should explicitly separate:
- lightweight synchronous reads/writes
- long-running async execution work

### 5.4 Monorepo integration is the most rational early shape

At this stage, separating the backend into many independent services would add operational overhead too early.
One integrated backend is the right default until real scaling pressure proves otherwise.

## 6. Required API Surfaces

This recommended API shape is expected to cover:

- auth-bound current user/session context
- workspace list/read/write
- run launch/status/result
- onboarding continuity
- provider/accounting-related product surfaces
- result/artifact lookup for return-use loops

## 7. Recommended Route Family Direction

Suggested route families:

- `/api/me/*`
- `/api/workspaces/*`
- `/api/runs/*`
- `/api/results/*`
- `/api/onboarding/*`
- `/api/providers/*`

## 8. Alternatives Considered

### 8.1 GraphQL
Rejected as first choice.
Too much complexity for this stage.

### 8.2 tRPC
Useful in some environments, but weaker as a canonical long-run public contract for this project.

### 8.3 Multi-service-first backend
Rejected for now.
Adds too much operational complexity too early.

### 8.4 Sync-only API
Rejected.
Incompatible with Nexa’s long-running execution reality.

## 9. PASS / FAIL Interpretation

This decision should be treated as `PASS` for Gate 4.5 if the project accepts:

`REST + monorepo integrated backend + mixed sync/async execution boundary`

If the project rejects that direction, Gate 4.5 remains `FAIL`.

## 10. Final Statement

Nexa should adopt:
- REST as the canonical API style
- a monorepo integrated backend as the initial service shape
- a mixed sync + async/background execution model

That is the best balance of:
- implementation simplicity
- web/mobile compatibility
- long-running execution reality
- future public API clarity
