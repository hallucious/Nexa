# Web Application Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/web_application_implementation_plan.md`

## 1. Purpose

This plan implements the browser-accessible product layer.

It turns the backend vertical slice into a usable product flow for a freelancer who is not using curl, CLI tools, or internal operator surfaces.

## 2. Governing references

- `docs/specs/saas/web_application_and_user_journey_spec.md`
- `docs/specs/saas/contract_review_product_spec.md`
- `docs/specs/saas/file_ingestion_and_document_safety_spec.md`
- `docs/specs/saas/provider_catalog_billing_and_quota_spec.md`

## 3. Goals

1. Provide a real browser journey from auth to result reading.
2. Make quarantine, queued, running, completed, and failed states understandable.
3. Render contract-review output clearly enough for non-technical users.
4. Keep plan/account/pricing behavior aligned with backend truth.
5. Avoid frontend shortcuts that hide real backend state.

## 4. Core implementation decisions

- Next.js is the browser shell,
- Clerk handles browser auth,
- API calls use typed wrappers,
- quarantine UX is mandatory,
- template-driven contract review is the first high-value path,
- browser product comes before graph editor or advanced builder UX.

## 5. Work packages

### Package W1 — App shell and auth
Outcomes:
- sign-in/sign-up flow works,
- protected routes require a valid session,
- token injection into API calls is stable,
- navigation exposes dashboard/account/pricing cleanly.

### Package W2 — Workspace and dashboard flow
Outcomes:
- workspace list and selection work,
- empty and first-use states are understandable,
- route structure mirrors product mental model.

### Package W3 — Upload and quarantine UX
Outcomes:
- upload flow integrates presign/direct-upload/confirm,
- quarantine/scanning/rejected/safe states are visible,
- run button remains gated until file is safe.

### Package W4 — Run submission and polling
Outcomes:
- run submission returns quickly,
- polling is resilient,
- terminal states are visible and navigable,
- failures are understandable without leaking internals.

### Package W5 — Result reading UX
Outcomes:
- clause list and risk levels render clearly,
- question list renders clearly,
- source references remain meaningful,
- trace/result viewers remain consistent with backend viewmodels.

### Package W6 — Account and pricing surfaces
Outcomes:
- current plan is visible,
- upgrade flow exists,
- plan/provider restrictions are explainable,
- account surface is understandable without operator knowledge.

## 6. Integration requirements

- Upload flow must respect quarantine truth.
- Run flow must respect async queue truth.
- Pricing/account surfaces must reflect backend billing/quota truth.
- i18n must align with en/ko translation discipline already present.

## 7. UX safety requirements

The UI must ensure:
- rejected files are actionable,
- blocked runs due to plan/provider mismatch are understandable,
- loading states are not mistaken for silent failure,
- raw internal error payloads do not leak into the browser experience.

## 8. Completion criteria

This plan is complete only if:
1. a freelancer can sign in and reach the dashboard,
2. a contract file can be uploaded and pass through quarantine visibly,
3. a run can be submitted and polled,
4. the result can be read in the browser,
5. pricing/account surfaces exist,
6. the browser flow is usable without operator intervention.
