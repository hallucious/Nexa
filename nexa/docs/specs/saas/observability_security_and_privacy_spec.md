# Nexa Observability, Security, and Privacy Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Safety and public-operation specification
Authority scope: Observability, redaction, rate limits, privacy, GDPR, headers, and public exposure safety
Recommended path: `docs/specs/saas/observability_security_and_privacy_spec.md`

## 1. Purpose

This document defines the minimum safety rules that make the Nexa SaaS fit for public operation.

Its purpose is to fix:
- what observability is allowed to contain,
- what it must never contain,
- how public request traffic is bounded,
- how privacy and GDPR are handled,
- and which browser-facing security measures are baseline requirements.

## 2. Public-operation principle

A SaaS that processes contracts and user documents must not treat observability and security as optional polish.
They are product requirements.

## 3. Observability goals

The observability system must help operators answer:
- what failed,
- how often it failed,
- how long it took,
- where the bottleneck is,
- and whether a provider or worker or queue path is degraded.

It must do this without leaking:
- document content,
- credentials,
- or direct personal identity data.

## 4. Redaction is mandatory

Redaction is not a best-effort rule.
It is a hard requirement before data reaches:
- logs,
- traces,
- metrics labels,
- or error tracking payloads.

## 5. Forbidden observability content

The following must never enter the observability surface:

1. extracted document text,
2. rendered prompt content that contains user input,
3. provider raw output content,
4. email addresses,
5. raw user ids,
6. Clerk subject values,
7. JWTs,
8. presigned URLs,
9. API keys,
10. AWS credentials,
11. any user data that would create a privacy incident if later exposed.

## 6. Allowed observability content

Allowed observability content is limited to safe operational identifiers and summaries such as:
- run id,
- workspace id,
- template id,
- opaque user reference,
- status codes,
- durations,
- queue depth,
- scan duration,
- failure class,
- and normalized query labels.

## 7. SQL observability rule

Raw SQL text is forbidden by default.

This rule exists because SQL instrumentation may capture parameterized values or other user-linked fragments.
The SaaS must prefer:
- operation type,
- table name,
- and internal query label

over raw SQL snippets.

## 8. Sentry behavior

Sentry is used for error tracking, but:
- request bodies must not be sent,
- default PII sending must be disabled,
- and event scrubbing must remove any forbidden content that still reaches the edge of the system.

## 9. OpenTelemetry behavior

OTel traces may exist, but span attributes must be scrubbed before export.
The system must not rely on “we will remember not to emit secrets” as the only defense.

## 10. HTTP logging rule

HTTP logs must be intentionally narrow.
They should carry:
- method,
- path,
- status,
- duration,
- and a request identifier,

but not request or response bodies.

## 11. Log retention

Observability retention must be bounded.
Long retention without strict need is not a virtue when sensitive workloads are involved.

## 12. Rate limiting

The public SaaS must rate-limit:
- authenticated general usage,
- run submission,
- upload initiation,
- and unauthenticated traffic.

Rate limiting is both:
- abuse protection,
- and cost protection.

## 13. CORS rule

The public SaaS must not use wildcard CORS in production.
Only explicitly allowed origins are valid.

## 14. Input safety boundary

Before a run is accepted, the SaaS must apply input-safety rules to detect:
- credential leakage,
- policy-relevant PII patterns,
- or other disallowed inbound content forms defined by product policy.

This is distinct from file-level safety and does not replace it.

## 15. GDPR behavior

The SaaS must support user deletion in a way that is consistent with:
- immutable operational history,
- mutable identity-linked tables,
- and object storage cleanup.

A valid GDPR path must:
- delete authoritative identity,
- delete mutable user-linked state where appropriate,
- delete user-owned file objects,
- and preserve immutable history without in-place mutation.

## 16. Security headers

The baseline SaaS must apply security headers appropriate for public browser delivery.
At minimum the baseline must explicitly cover:
- content type sniffing protection,
- frame embedding policy,
- HSTS,
- and content security policy.

## 17. Non-goals

This document does not define:
- advanced fraud systems,
- enterprise DLP,
- region-specific regulatory mapping beyond the baseline deletion/privacy model,
- or customer-managed security infrastructure.

## 18. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. the SaaS can be observed meaningfully,
2. document content cannot leak through normal observability paths,
3. raw credentials and raw identity fields are blocked from observability,
4. raw SQL text is not treated as safe default telemetry,
5. public request rates are bounded,
6. production CORS is explicit,
7. GDPR deletion works without mutating immutable history,
8. and public-facing security headers are present.
