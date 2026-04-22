# Capability Activation and Expansion Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/capability_activation_and_expansion_implementation_plan.md`

## 1. Purpose

This plan defines how the product surface expands safely over time.

It does not treat raw route count as success.
It treats user-facing and operator-facing capability bundles as the unit of activation.

## 2. Governing spec references

- `docs/specs/saas/capability_activation_and_expansion_spec.md`
- `docs/specs/saas/web_application_and_user_journey_spec.md`

## 3. Goals

1. Public surface expands in capability bundles rather than uncontrolled route exposure.
2. Each bundle is backed by completed behavior, tests, and operator support.
3. Browser product matures before mobile expansion.
4. Community and ecosystem features remain deferred until justified.
5. MCP arrives only after the product is operationally stable.

## 4. Core implementation decisions

- `NEXA_SURFACE_PROFILE` expresses bundle selection
- capability bundles are cumulative and testable
- product expansion follows real user value and operational readiness
- browser-first is mandatory before mobile
- PMF signals gate major expansion

## 5. Work packages

### Package X1 — Bundle registry and route mapping

Required outcomes:
- bundle-to-route mapping lives in one place
- route exposure is profile-driven
- bundle activation is contract-tested

### Package X2 — Core product bundles

Required outcomes:
- `core`, `async_control`, `upload`, `templates`, `provider_management`, `result_history`, `billing`, `admin`
- each bundle activated only when underlying behavior is ready

### Package X3 — PMF-gated expansion

Required outcomes:
- mobile start criteria encoded in planning and rollout checklists
- public sharing deferred behind PMF and moderation prerequisites
- MCP deferred behind operational stability prerequisites

### Package X4 — Release gating

Required outcomes:
- bundle activation checklist
- staging verification before public enablement
- rollback strategy for newly exposed bundles

## 6. Testing and gating requirements

Every bundle must have:
- route-set contract tests
- happy-path feature tests
- permission tests where relevant
- observability sanity checks where relevant
- rollback or disable path

## 7. Exit criteria

This segment is complete only if:

1. surface activation follows capability readiness rather than route count,
2. each bundle can be turned on intentionally and tested,
3. mobile and MCP remain gated by real readiness conditions,
4. expansion does not outrun product support and operational maturity.
