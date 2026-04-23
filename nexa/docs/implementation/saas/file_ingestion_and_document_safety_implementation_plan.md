# File Ingestion and Document Safety Implementation Plan

Document type: Segment implementation plan  
Status: Draft  
Recommended path: `docs/implementation/saas/file_ingestion_and_document_safety_implementation_plan.md`

## 1. Purpose

This plan implements the document ingestion pipeline for the SaaS product.

Its job is not merely to accept uploads. It must ensure that uploaded files are:
- durably tracked,
- quarantined before use,
- scanned for file-level risk,
- extracted within bounded limits,
- promoted to usable state only when safe.

## 2. Governing references

- `docs/specs/saas/file_ingestion_and_document_safety_spec.md`
- `docs/specs/saas/observability_security_and_privacy_spec.md`
- `docs/specs/saas/operations_recovery_and_admin_surface_spec.md`

## 3. Goals

1. Support direct-to-object-store uploads.
2. Make upload state durable and queryable.
3. Prevent unsafe files from reaching execution.
4. Bound extraction cost and runtime.
5. Make rejection causes deterministic and auditable.

## 4. Core implementation decisions

- browser uploads directly through presigned URLs,
- Postgres stores authoritative upload and scan state,
- S3 stores file objects only,
- ClamAV performs file-level scanning,
- text-level safety complements but does not replace file-level scanning,
- only `safe` files may be referenced in run submission.

## 5. Work packages

### Package I1 — Presign and upload identity
Outcomes:
- presign endpoint issues upload ids and short-lived URLs,
- initial upload record exists before use,
- size/type preconditions are checked early.

### Package I2 — Quarantine state machine
Outcomes:
- upload status transitions follow the approved state model,
- transitions are append-only in event history,
- status endpoint supports frontend polling cleanly.

### Package I3 — File-level scanning
Outcomes:
- ClamAV integration exists,
- malware, timeout, and scan failure cases are explicit,
- rejected objects are cleaned according to lifecycle policy.

### Package I4 — Extraction pipeline
Outcomes:
- PDF and DOCX extraction are bounded,
- malformed/protected files fail deterministically,
- extracted length is recorded for later admission logic.

### Package I5 — Execution gating
Outcomes:
- run submission rejects non-safe files,
- file identity is carried forward unambiguously,
- upload state and object state can be reconciled operationally.

### Package I6 — User/operator feedback
Outcomes:
- users see clear upload state and rejection feedback,
- operators can inspect scan history through admin pathways,
- rejection notifications can be emitted if configured.

## 6. Required runtime surfaces

Tables:
- `file_uploads`
- `file_upload_events`

Modules:
- file upload API
- S3 client
- file extractor
- file safety scanner
- file upload store

Supporting integrations:
- cleanup jobs
- admin upload review surface
- safe observability around scan outcomes and timings

## 7. Safety and privacy requirements

The implementation must ensure:
- no raw extracted text reaches logs/traces,
- object URLs are not emitted into observability output,
- original filenames are not treated as automatically safe logging fields,
- rejection reasons are machine-readable and UX-mappable.

## 8. Failure handling

Must explicitly handle:
- unconfirmed upload,
- missing object after confirm,
- MIME mismatch,
- magic-byte mismatch,
- password-protected PDF,
- malformed document,
- scan timeout,
- scanner unavailable,
- extraction timeout,
- over-limit extraction.

## 9. Completion criteria

This plan is complete only if:
1. presign/confirm/status work end-to-end,
2. quarantine and scan state are durable,
3. only safe files can enter execution,
4. rejected files have stable reason codes and cleanup behavior,
5. extraction limits are enforced,
6. upload event history is append-only.
