# Contract Review Vertical Slice Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/contract_review_vertical_slice_implementation_plan.md`

## 1. Purpose

This plan implements the first product vertical slice: contract review for freelancers.

It is the first concrete product proof that the SaaS system delivers user value beyond infrastructure readiness.

## 2. Governing spec references

- `docs/specs/saas/contract_review_product_spec.md`
- `docs/specs/saas/file_ingestion_and_document_safety_spec.md`
- `docs/specs/saas/provider_catalog_billing_and_quota_spec.md`

## 3. Goals

1. A real uploaded document can enter the product flow.
2. The contract-review circuit runs to completion.
3. Output is structured, explainable, and source-linked.
4. The use case works on the default lower-cost plan path.
5. The output shape is stable enough for browser rendering and support.

## 4. Core implementation decisions

- initial killer use case remains contract review
- default free-path execution uses Claude Haiku 3
- source references use character offsets, not viewer page numbers
- clause ids are deterministic
- result envelope remains machine-readable and UI-friendly

## 5. Work packages

### Package C1 — Starter template registration

Required outcomes:
- contract review appears in starter templates
- template metadata describes file acceptance and category accurately
- apply-template flow materializes a usable workspace configuration

### Package C2 — Prompt and circuit assets

Required outcomes:
- circuit file exists and passes validation
- prompts exist, are versionable, and remain structured-output friendly
- node contracts are clear about produced fields

Expected assets:
- contract review `.nex`
- clause extraction prompt
- plain-language explanation prompt
- question generation prompt

### Package C3 — Output contract enforcement

Required outcomes:
- result envelope shape is validated
- clause ids are deterministic
- source references survive all steps
- explanation and question outputs remain structured rather than prose blobs

### Package C4 — Integration with upload and execution

Required outcomes:
- safe uploaded file becomes input reference
- extracted text enters the circuit through defined context
- final result is retrievable from the normal product result flow

### Package C5 — Quality and fallback behavior

Required outcomes:
- model failures handled cleanly
- malformed partial outputs produce deterministic failure or fallback paths
- missing source references are treated as invalid result quality, not silently ignored

## 6. Test requirements

Minimum tests:

1. uploaded contract can run end-to-end
2. output contains clause list and question list
3. clause ids remain deterministic across identical reruns
4. source references remain present
5. free-plan default model path works
6. invalid structured output is surfaced deterministically

## 7. Exit criteria

This segment is complete only if:

1. a freelancer can upload a contract and get a meaningful result,
2. the result is structured enough for UI and support use,
3. default-cost path is commercially viable,
4. product demos and real-user testing can be based on this flow without manual intervention.
