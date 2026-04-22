# SaaS Implementation Plan Index

Document type: Implementation plan index  
Status: Draft  
Recommended path: `docs/implementation/saas/saas_implementation_plan_index.md`

## 1. Purpose

This document is the entry point for the SaaS implementation plan family.

It explains how the approved SaaS specs and the approved SaaS completion plan should be translated into implementation work. It is intended to help a future human operator or another AI system understand the implementation program without needing to reconstruct the full context from scattered notes.

This index answers four questions:
1. which implementation plans exist,
2. what each plan is responsible for,
3. what order the plans should be executed in,
4. which shared rules apply across all implementation sectors.

## 2. Governing references

Primary planning authority:
- `nexa_saas_completion_plan_v0.4.md`

Primary SaaS spec family:
- `docs/specs/saas/saas_spec_index.md`
- `docs/specs/saas/saas_foundation_and_governance_spec.md`
- `docs/specs/saas/async_execution_and_run_state_spec.md`
- `docs/specs/saas/provider_catalog_billing_and_quota_spec.md`
- `docs/specs/saas/file_ingestion_and_document_safety_spec.md`
- `docs/specs/saas/contract_review_product_spec.md`
- `docs/specs/saas/web_application_and_user_journey_spec.md`
- `docs/specs/saas/observability_security_and_privacy_spec.md`
- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`
- `docs/specs/saas/capability_activation_and_expansion_spec.md`

## 3. Plan family map

### 3.1 Foundation and platform
`foundation_and_platform_implementation_plan.md`

Shared implementation rules for migration discipline, startup discipline, environment variable discipline, repository placement, and cross-sector invariants.

### 3.2 Async execution and worker
`async_execution_and_worker_implementation_plan.md`

Implements non-blocking run submission, worker processing, durable submission persistence, and queue recovery.

### 3.3 Provider, billing, and quota
`provider_billing_and_quota_implementation_plan.md`

Implements the canonical provider catalog, pricing data, cost estimation, quota enforcement, and Stripe-backed subscription flows.

### 3.4 File ingestion and document safety
`file_ingestion_and_document_safety_implementation_plan.md`

Implements presigned uploads, quarantine, ClamAV scanning, extraction, and the safe-file gate before execution.

### 3.5 Contract review vertical slice
`contract_review_vertical_slice_implementation_plan.md`

Implements the first end-to-end user-value flow: upload a contract, process it, and return structured contract-review output.

### 3.6 Web application
`web_application_implementation_plan.md`

Implements the browser user journey, including auth, dashboard, upload flow, run submission, result reading, and pricing/account surfaces.

### 3.7 Observability, security, and privacy
`observability_security_and_privacy_implementation_plan.md`

Implements the safe-public-operation layer: Sentry, OTel, redaction, rate limiting, explicit CORS, security headers, and GDPR-aligned deletion.

### 3.8 Operations, recovery, and admin surface
`operations_recovery_and_admin_surface_implementation_plan.md`

Implements operational durability and operator tooling: backup, restore, cleanup, archive visibility, admin actions, and incident support.

### 3.9 Capability activation and expansion
`capability_activation_and_expansion_implementation_plan.md`

Implements capability-bundle activation, staged public surface growth, browser-first rollout, and later mobile/MCP expansion gates.

## 4. Recommended execution order

1. Foundation and platform
2. Async execution and worker
3. Provider, billing, and quota decision layer
4. File ingestion and document safety
5. Contract review vertical slice
6. Web application
7. Observability/security core
8. Operations/recovery/admin surface
9. Capability activation and later expansion

This order reflects the bottleneck logic already fixed by the completion plan: non-blocking execution, safe document ingestion, and browser usability come before broader expansion.

## 5. Shared rules across the family

1. Specs govern behavior; implementation plans govern execution order.
2. No implementation plan may silently violate table mutability, PII placement, or source-of-truth rules.
3. Every runtime surface described in a plan must appear in file inventory, schema, migration, and env documentation where relevant.
4. Public-surface growth must not outrun observability, security, and admin support.
5. Browser product proof comes before mobile expansion.
6. Deferred sectors remain deferred until their gate conditions are met.

## 6. Shared completion standard

A sector plan is not complete unless:
- the governing spec is satisfied,
- the runtime surfaces exist,
- schema/migration changes are consistent,
- tests exist and pass,
- cross-sector side effects are documented,
- no hidden governance contradiction is introduced.
