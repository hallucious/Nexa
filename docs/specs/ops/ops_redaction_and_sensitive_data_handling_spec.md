# Operations Redaction and Sensitive Data Handling Specification

## Recommended save path
`docs/specs/ops/ops_redaction_and_sensitive_data_handling_spec.md`

## 1. Purpose

This document defines how the AI-assisted operations layer must handle sensitive information.

Its purpose is to ensure that operational usefulness never depends on unrestricted access to customer-confidential or secret-bearing content.

## 2. Scope

This specification governs:

1. sensitive-data classes,
2. redaction requirements,
3. allowed diagnostic transforms,
4. prompt-input restrictions for operations AI,
5. output restrictions for summaries and recommendations.

## 3. Sensitive-data classes

Minimum sensitive-data classes:

1. confidential document content,
2. personal data and PII,
3. credentials and secrets,
4. JWTs and auth artifacts,
5. presigned URLs and temporary access links,
6. billing-sensitive identifiers,
7. provider raw request/response payloads containing customer content.

## 4. Redaction rule

Sensitive data must be removed, transformed, or replaced before entering the operations AI layer.

Default treatment:

1. remove if not required,
2. hash if identity continuity is required,
3. summarize if diagnostic meaning is required,
4. tokenize or replace if categorical meaning is required.

## 5. Allowed diagnostic transforms

Permitted transforms include:

1. opaque identifiers,
2. one-way hashes,
3. category labels,
4. severity flags,
5. length/count summaries,
6. policy-match indicators,
7. bounded extracts approved by policy.

Raw text convenience is not a valid justification.

## 6. Forbidden inputs to operations AI

The operations AI must not be prompted with:

1. raw uploaded contract text,
2. raw clause text,
3. plain-language explanation text created for end users,
4. prompt-rendered content containing customer documents,
5. raw provider completions,
6. API keys,
7. JWT bodies,
8. raw email addresses unless separately approved.

## 7. Output restrictions

The operations AI must not emit:

1. document excerpts,
2. customer payload text,
3. raw secrets,
4. raw credential strings,
5. raw tokens,
6. unrestricted personal data.

If summary output includes identifiers, they must be redacted or transformed identifiers, not raw sensitive values.

## 8. Redaction provenance

Every evidence bundle should indicate:

1. whether redaction was applied,
2. what class of redaction was applied,
3. whether any diagnostic fidelity was reduced.

The system must not hide the fact that evidence has been redacted.

## 9. Failure behavior under missing context

If redaction removes critical context needed for confident recommendation:

1. the system must lower confidence,
2. the system must say that evidence is insufficient,
3. the system must escalate to human review rather than compensate with guesswork.

## 10. Acceptance criteria

A conforming implementation satisfies this specification only if:

1. sensitive-data classes are explicitly defined,
2. operations AI does not consume raw confidential content by default,
3. outputs are redacted appropriately,
4. evidence bundles report redaction provenance,
5. low-context situations reduce confidence instead of increasing hallucination risk.
