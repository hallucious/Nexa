# Nexa Provider Catalog, Billing, and Quota Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Economic and provider-governance specification
Authority scope: Provider model, plan access, cost ratios, billing, and quota behavior
Recommended path: `docs/specs/saas/provider_catalog_billing_and_quota_spec.md`

## 1. Purpose

This document defines the commercial and provider-governance layer of the Nexa SaaS.

Its purpose is to fix:
- which provider/model tiers exist,
- which plans may access which tiers,
- how Nexa pays providers,
- how users are charged,
- how quota is enforced,
- and how estimated versus actual cost is handled.

Without this document, the product would have ambiguous economics and ambiguous provider behavior.

## 2. Provider operating model

### 2.1 Initial operating model

The initial SaaS uses **server-managed provider keys only**.

This means:
- Nexa holds provider credentials,
- Nexa pays provider bills,
- Nexa exposes model access according to plan,
- and Nexa enforces both usage and cost controls at the platform layer.

### 2.2 BYOK status

Bring-your-own-key is deferred.
It is not part of the baseline SaaS.

### 2.3 Why BYOK is deferred

BYOK would materially change:
- support complexity,
- cost accounting,
- security responsibility,
- provider-binding persistence,
- and product segmentation.

The initial freelancer-focused product does not need that complexity.

## 3. Canonical provider catalog

The provider catalog below is the only authoritative catalog for the baseline SaaS.

| Provider | Model | Tier | Plan availability | Role |
|---|---|---|---|---|
| Anthropic | Claude Haiku 3 | economy | Free, Pro, Team | default low-cost baseline |
| Anthropic | Claude Sonnet 4 | standard | Pro, Team | higher quality standard path |
| OpenAI | GPT-4o | standard | Pro, Team | alternative standard path |

No other wording elsewhere should redefine this catalog.

## 4. Model access rules

### 4.1 Free plan

Free users may access only:
- Claude Haiku 3

If a free-plan run requests Sonnet 4 or GPT-4o, the request must be rejected with a machine-readable plan/tier reason.

### 4.2 Pro and Team plans

Pro and Team may access:
- Claude Haiku 3,
- Claude Sonnet 4,
- GPT-4o.

### 4.3 Default selection rule

The default model is Claude Haiku 3 unless:
- the circuit explicitly asks for another model,
- or a later user-facing selection surface is permitted by policy.

## 5. Provider binding semantics

The SaaS must distinguish:

1. the **provider key reference** used operationally,
2. the **model** chosen for the run,
3. the **workspace authorization** to use a provider,
4. and the **secret storage** where the credential actually lives.

The product must not store raw API keys in product tables.

## 6. Cost catalog

### 6.1 Provider cost catalog role

The SaaS maintains a cost catalog that expresses relative provider/model costs in a durable product-readable form.

### 6.2 Why the catalog exists

The billing and quota layer cannot rely on vague “cheap” vs “expensive” concepts.
It must be able to:
- estimate pre-run cost,
- record post-run cost,
- and compare actual usage to plan caps.

### 6.3 Refresh rule

The product must have an explicit refresh mechanism for cost catalog values.
The catalog must not be treated as magically current.

The refresh mechanism may later be:
- manual operator update,
- scheduled sync job,
- or controlled admin workflow.

## 7. Stripe role

Stripe is the authoritative payment and subscription processor.

Postgres stores the product-local subscription view for application behavior, but when Stripe and Postgres diverge:
- Stripe is authoritative,
- Postgres is reconciled.

## 8. Plan structure

| Plan | Price | Run-count limit | Estimated cost cap | Allowed models |
|---|---|---|---|---|
| Free | $0 | 3 runs/month | $0.50/month estimated | Haiku 3 only |
| Pro | $19/month | Unlimited count | $15/month estimated | Haiku 3, Sonnet 4, GPT-4o |
| Team | $49/seat/month | Unlimited count | $40/month estimated | Same as Pro |

These values may later evolve, but any change must update this document or its successor.

## 9. Quota is three-axis, not one-axis

A conforming implementation must treat quota as at least three separate controls.

### 9.1 Axis 1 — run count

This limits:
- how many runs a user may submit in a period.

### 9.2 Axis 2 — estimated cost

This blocks:
- runs that are likely to exceed the user’s plan cost allowance before they start.

### 9.3 Axis 3 — actual cost

This records:
- what the run actually cost after provider usage is known.

These axes exist for different reasons and must not be collapsed into a single number.

## 10. Pre-run estimation

### 10.1 Why estimation exists

Without pre-run estimation, the SaaS can approve runs that already violate the economic structure of the plan.

### 10.2 Accuracy expectation

Pre-run estimation does not need to be perfect in the baseline SaaS.
It must be good enough to:
- catch obvious overage,
- and stop economically invalid runs early.

### 10.3 Inputs to estimation

The estimate may consider:
- model choice,
- document size,
- expected token volume,
- circuit complexity,
- and output expectations.

## 11. Post-run actual cost accounting

### 11.1 Why actual cost still matters

Estimates can be wrong.
Therefore actual provider cost must still be captured and aggregated.

### 11.2 Soft vs hard limit behavior

The SaaS may:
- warn when actual cost is nearing or exceeding the target,
- then hard-block later runs if the economic threshold is crossed.

The important rule is that the platform must remain economically self-consistent.

## 12. Provider failure and support consequences

Because Nexa owns provider keys in the baseline model:
- Nexa owns the user’s experience of provider failures,
- Nexa can probe provider health directly,
- Nexa can support the end-to-end execution path,
- and Nexa must not hide behind a user-managed-key boundary.

This is one reason the server-managed model is the correct starting point.

## 13. Deferred provider expansion

The following are not baseline:
- Gemini,
- Perplexity,
- Claude Opus,
- BYOK,
- enterprise tenant-specific provider isolation.

These may be added later only with explicit specification updates.

## 14. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. the provider catalog is singular and unambiguous,
2. plan access matches the canonical catalog,
3. server-managed keys remain the baseline model,
4. billing authority is clearly split between Stripe and product state,
5. quota is treated as run-count plus estimated-cost plus actual-cost,
6. pre-run economic rejection is possible,
7. post-run actual-cost recording is possible,
8. and provider support responsibility is internally consistent.
