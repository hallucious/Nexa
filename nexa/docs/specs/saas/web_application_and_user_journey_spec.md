# Nexa Web Application and User Journey Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Web product specification
Authority scope: Browser product behavior, screen groups, route-facing journeys, and i18n baseline
Recommended path: `docs/specs/saas/web_application_and_user_journey_spec.md`

## 1. Purpose

This document defines the browser-facing product behavior of the Nexa SaaS.

Its purpose is to fix:
- what the minimum web application must let a user do,
- which screen families are required,
- how the contract-review journey behaves from sign-in to result,
- and how the product should present upload, run, result, and account state.

## 2. Role of the web product

The web product is the primary initial delivery surface of the SaaS.

This means:
- it is earlier than mobile,
- it is the main PMF surface,
- and it is the first place where the product must feel coherent to a non-technical user.

## 3. Minimum required screen groups

The minimum browser product must include screen groups for:

1. authentication entry,
2. dashboard/workspace access,
3. contract-review run initiation,
4. result viewing,
5. trace/review visibility,
6. pricing,
7. account/subscription management.

## 4. Authentication journey

The user journey begins with sign-in/sign-up.
If the user is not authenticated, protected product areas must not be accessible.

The baseline product depends on:
- an external identity provider for sign-in,
- a browser session,
- and backend JWT validation.

## 5. Dashboard role

The dashboard must act as the user’s entry point into product usage.
At minimum it should help the user:
- find their workspace,
- start work,
- and return to recent product state.

## 6. Contract review run journey

A valid contract-review user journey should look like this:

1. user enters run page,
2. user sees the contract-review template or entry point,
3. user uploads a document,
4. user waits while upload and safety state resolve,
5. user submits the run,
6. the system shows progress without blocking the browser request,
7. the user is taken to the result experience when complete.

## 7. Upload UX requirements

The product must surface upload trust state clearly.

It must be possible for a user to distinguish:
- uploading,
- scanning/quarantine,
- ready,
- rejected.

The user must not be forced to infer file readiness from indirect product clues.

## 8. Run state UX requirements

The product must present asynchronous run state in a user-comprehensible way.

At minimum the user should be able to tell:
- the run was accepted,
- the run is still processing,
- the run completed,
- or the run failed.

The product should not depend on the user keeping one HTTP request open.

## 9. Results UX requirements

The result experience must present:
- the clause list,
- each clause’s explanation,
- why-it-matters framing,
- and the question list.

This should feel like a productized review flow, not a raw internal execution dump.

## 10. Trace and transparency

The product may also expose trace-related information.
The baseline requirement is not deep technical transparency for every user, but enough state visibility that:
- the product feels trustworthy,
- and support/advanced inspection can happen when needed.

## 11. Provider and template surfaces

The browser product may expose:
- template gallery,
- provider setup guidance,
- result history,
- and artifact views

when the corresponding capability bundles are active.

These should not be treated as always-on assumptions if the product surface profile is still constrained.

## 12. Pricing and account UX

A real SaaS needs visible commercial surfaces.

The browser product must support:
- plan visibility,
- upgrade path,
- subscription state visibility,
- and account management.

Without these, billing exists technically but not as a usable product.

## 13. Internationalization baseline

The web product baseline supports:
- English,
- Korean.

The translation model must be coherent enough that future UI text can be localized without redefining product meaning.

## 14. Browser PMF rule

This product surface is the primary PMF-testing surface.
That means:
- mobile does not outrank it,
- community features do not outrank it,
- and MCP does not outrank it.

The browser product is where the first real user loop must succeed.

## 15. Non-goals

This document does not define:
- visual circuit editing,
- team collaboration UI,
- community/public share UI,
- deep enterprise admin console,
- or mobile-specific interaction models.

## 16. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. a user can authenticate and enter the product,
2. a user can reach the contract-review flow from the browser,
3. upload readiness and rejection states are visible,
4. a run can be submitted without a synchronous waiting pattern,
5. results are understandable in the browser,
6. pricing and account state are available as product surfaces,
7. the browser experience is sufficient to test PMF before mobile is attempted.
