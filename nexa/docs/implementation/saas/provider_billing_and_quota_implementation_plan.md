# Provider, Billing, and Quota Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/provider_billing_and_quota_implementation_plan.md`

## 1. Purpose

This plan implements the commercial and provider-control layer of the SaaS system.

It is responsible for making sure that:
- the provider catalog is real runtime behavior,
- plan restrictions are machine-enforced,
- run-count and cost-based quota are enforced consistently,
- Stripe-backed subscription state and product access stay aligned.

## 2. Governing references

- `docs/specs/saas/provider_catalog_billing_and_quota_spec.md`
- `docs/specs/saas/saas_foundation_and_governance_spec.md`
- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`

## 3. Goals

1. Enforce canonical provider/model access by plan.
2. Turn pricing data into real run-admission behavior.
3. Add preflight and post-run cost accounting.
4. Keep Stripe and Postgres subscription state reconcilable.
5. Preserve the MVP server-managed-key model.

## 4. Core implementation decisions

- provider/model access is checked before run launch,
- pricing authority comes from `provider_cost_catalog`,
- run-count, estimated-cost, and actual-cost axes are distinct,
- Stripe is authoritative when plan divergence occurs,
- BYOK remains out of scope.

## 5. Work packages

### Package P1 — Canonical provider catalog runtime
Outcomes:
- provider/model rows exist in DB,
- plan-access decisions are deterministic,
- invalid model selection fails with stable reason codes.

### Package P2 — Pricing catalog refresh discipline
Outcomes:
- monthly refresh path exists,
- manual operator refresh path exists,
- fallback behavior is explicit if catalog refresh fails.

### Package P3 — Preflight cost estimation
Outcomes:
- estimated cost is computed before enqueue,
- confidence is explicit,
- over-cap runs are blocked early,
- model choice affects estimated cost.

### Package P4 — Quota enforcement runtime
Outcomes:
- run-count quota works,
- estimated-cost quota works,
- actual-cost settlement works,
- warnings and hard blocks follow the spec ordering.

### Package P5 — Stripe integration and reconciliation
Outcomes:
- checkout creation works,
- subscription read works,
- webhook updates work,
- webhook replay path exists,
- divergence resolution follows source-of-truth rules.

### Package P6 — User/admin visibility
Outcomes:
- user sees current plan and usage posture,
- admin can inspect and override safely,
- all override flows are audited.

## 6. Required runtime surfaces

Tables/stores:
- `provider_cost_catalog`
- `user_subscriptions`
- `quota_usage`
- provider cost catalog store
- subscription store
- quota usage store

Runtime modules:
- run preflight
- quota enforcement
- Stripe client
- Stripe webhook handler

## 7. Cross-sector integration

- Quota enforcement happens before queue enqueue.
- Actual-cost settlement happens after run completion.
- Browser pricing/account surfaces must reflect backend truth.
- Admin tools must expose replay/reset/override safely.

## 8. Failure handling

Must explicitly handle:
- missing pricing rows,
- stale catalog,
- duplicate webhook delivery,
- webhook failure,
- estimated-cost undercount,
- actual-cost overrun,
- plan/model mismatch.

## 9. Completion criteria

This plan is complete only if:
1. provider/model access is enforced,
2. free-plan higher-tier misuse is blocked,
3. preflight estimation runs before enqueue,
4. actual-cost settlement updates durable usage,
5. Stripe state and admin reconciliation both work,
6. server-managed provider key assumptions remain intact.
