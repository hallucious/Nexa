# Nexa SaaS Specification Index

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Specification index
Authority scope: SaaS productization and operation beyond the P0 server seam
Recommended path: `docs/specs/saas/saas_spec_index.md`

## 1. Purpose

This document is the top-level index for the Nexa SaaS specification family.

Its role is to translate the approved SaaS completion plan into a stable specification structure that can be read later by:
1. the current assistant,
2. a future assistant,
3. another AI system, or
4. a human reviewer

without requiring them to reconstruct the product from planning prose alone.

This index does not replace the detailed specifications below.
It identifies the boundaries of the SaaS system, the relationship between the sub-specifications, and the correct reading order.

## 2. Reading order

Read the documents in this order:

1. `saas_foundation_and_governance_spec.md`
2. `async_execution_and_run_state_spec.md`
3. `provider_catalog_billing_and_quota_spec.md`
4. `file_ingestion_and_document_safety_spec.md`
5. `contract_review_product_spec.md`
6. `web_application_and_user_journey_spec.md`
7. `observability_security_and_privacy_spec.md`
8. `operations_recovery_and_admin_surface_spec.md`
9. `capability_activation_and_expansion_spec.md`

This order is intentional:
- governance first,
- runtime and economic rules second,
- file and product behavior third,
- user-facing web behavior fourth,
- safety and operations fifth,
- controlled expansion last.

## 3. Specification family map

| File | Primary concern | Why it exists |
|---|---|---|
| `saas_foundation_and_governance_spec.md` | SaaS purpose, milestones, mutability rules, source-of-truth hierarchy | Prevents later contradictions about what is authoritative |
| `async_execution_and_run_state_spec.md` | Queue-backed execution, run states, recovery semantics | Defines the core runtime surface of the SaaS |
| `provider_catalog_billing_and_quota_spec.md` | Provider model, model access, billing, quota, pricing | Fixes the commercial and cost-governance layer |
| `file_ingestion_and_document_safety_spec.md` | Upload, quarantine, scanning, extraction, document trust | Fixes the document intake path |
| `contract_review_product_spec.md` | First killer use case | Fixes what the product actually does for the first user segment |
| `web_application_and_user_journey_spec.md` | Browser UX, route grouping, i18n, result flow | Fixes the web product behavior |
| `observability_security_and_privacy_spec.md` | Logging, tracing, redaction, rate limits, GDPR, headers | Fixes safe public operation |
| `operations_recovery_and_admin_surface_spec.md` | Backup, restore, cleanup, admin capabilities | Fixes operational durability and incident handling |
| `capability_activation_and_expansion_spec.md` | Surface profile expansion, mobile, MCP, deferred layers | Fixes how Nexa expands without destabilizing itself |

## 4. Scope of this specification family

This specification family covers the SaaS product surface that begins after the P0 proof is already in place.

It covers:
- asynchronous execution,
- document upload and safety,
- the first real product use case,
- web delivery,
- provider and plan governance,
- billing and quota,
- monitoring and security,
- recovery and operations,
- staged feature activation.

It does not cover:
- the low-level P0 implementation brief,
- the Nexa constitutional architecture documents,
- the visual circuit editor,
- enterprise-only features,
- self-hosted packaging,
- broad community features,
- a full AI-assisted operations copilot.

## 5. Authoritative planning source

This specification family is derived from `nexa_saas_completion_plan_v0.4.md`, which defined:
- the segment map,
- SaaS operability milestones,
- table mutability and retention categories,
- source-of-truth hierarchy,
- the canonical provider catalog,
- sprint sequencing,
- full file/schema/migration inventory,
- and the final governance cleanup around immutable records and GDPR handling.

This specification family converts that plan into a stable “what must be true” reference set.

## 6. Cross-document rules

The following rules apply to every document in this family:

1. Numbering starts at 1.
2. Documents are written in English spec style.
3. The files are not implementation briefs.
4. When a behavior is described in more than one file, only one file should be normative and the others should cross-reference it.
5. If a future implementation plan conflicts with these specifications on behavior, safety, or governance, the specifications govern.
6. If a future revision changes the product in a way that invalidates one of these files, the file must be updated rather than silently bypassed.

## 7. Product baseline defined by this family

The baseline SaaS promised by this family is:

- a freelancer can sign in,
- upload a contract,
- wait through quarantine and scan,
- submit a run without blocking the browser request lifecycle,
- receive a result with clause explanations and pre-signature questions,
- operate under an explicit provider/plan model,
- be governed by quota and billing rules,
- use a system that is observable, rate-limited, privacy-aware, recoverable, and supportable.

## 8. Normative relationship to later documents

This family is intended to stay valid even when later implementation detail changes.
That means the documents should preserve:
- invariants,
- boundaries,
- allowed behaviors,
- safety rules,
- governance rules,
- required user outcomes,
- and staged expansion logic.

Implementation details such as exact filenames, libraries, and deployment syntax may later move into implementation plans.

## 9. Deferred areas

These are intentionally outside the current SaaS baseline:
- visual circuit editing,
- BYOK,
- public sharing/community,
- enterprise SSO/SLA/export,
- self-hosted deployment,
- broad mobile-first prioritization,
- MCP as an immediate operational dependency,
- AI-assisted operations as a product-critical dependency.

## 10. Final reading rule

If a future reader wants to know:
- what Nexa SaaS is,
- what it must do,
- what it must not do,
- and how its major layers relate,

this index and the nine child specifications are the correct starting point.
