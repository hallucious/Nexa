# Observability, Security, and Privacy Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/observability_security_and_privacy_implementation_plan.md`

## 1. Purpose

This plan implements the safe-public-operation layer for the SaaS system.

It covers:
- Sentry,
- OpenTelemetry,
- redaction enforcement,
- rate limiting,
- CORS discipline,
- security headers,
- GDPR-aligned deletion behavior.

## 2. Governing references

- `docs/specs/saas/observability_security_and_privacy_spec.md`
- `docs/specs/saas/saas_foundation_and_governance_spec.md`
- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`

## 3. Goals

1. Operators can see failures and performance issues.
2. Observability never becomes a confidentiality leak path.
3. Public endpoints are bounded and hardened.
4. GDPR delete flows work without violating immutable record rules.
5. Security controls become real runtime behavior.

## 4. Core implementation decisions

- Sentry captures errors,
- OTel captures traces/metrics,
- redaction happens before sensitive payloads can escape,
- raw SQL text is not safe observability content,
- rate limiting is Redis-backed,
- production CORS uses explicit origins,
- immutable records remain untouched during GDPR deletion.

## 5. Work packages

### Package O1 — Sentry baseline
Outcomes:
- Sentry initializes in API runtime,
- worker failures can be reported,
- request bodies and default PII remain disabled,
- scrubber hook is testable.

### Package O2 — OTel baseline
Outcomes:
- request/database/Redis traces exist,
- normalized identifiers replace unsafe raw fields,
- trace quality supports incident diagnosis,
- SQL statement leakage is blocked.

### Package O3 — Redaction enforcement
Outcomes:
- document content scrubbed,
- PII scrubbed,
- credentials/tokens scrubbed,
- request/response body logging disabled,
- automated tests assert forbidden content absence.

### Package O4 — Public edge hardening
Outcomes:
- user/IP rate limits enforced,
- upload and run endpoints explicitly throttled,
- CORS origins explicit,
- security headers active.

### Package O5 — GDPR deletion path
Outcomes:
- identity removed from authoritative identity layers,
- mutable identity-bearing tables deleted/cleared,
- immutable operational history preserved,
- object storage artifacts deleted,
- audit evidence survives.

## 6. Required tests

Minimum tests should cover:
- Sentry scrubbing,
- OTel scrubbing,
- absence of forbidden span fields,
- no raw request bodies in logs,
- rate limit enforcement,
- production CORS behavior,
- GDPR deletion with immutable record preservation.

## 7. Completion criteria

This plan is complete only if:
1. failures show up in Sentry,
2. traces exist without leaking confidential content,
3. no raw SQL appears in traces,
4. rate limits work on sensitive endpoints,
5. explicit CORS and security headers are active,
6. GDPR deletion works without touching immutable records.
