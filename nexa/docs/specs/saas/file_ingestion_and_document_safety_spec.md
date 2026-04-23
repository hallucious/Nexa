# Nexa File Ingestion and Document Safety Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: File intake and safety specification
Authority scope: Upload flow, quarantine, scanning, extraction, safety, and usable-file readiness
Recommended path: `docs/specs/saas/file_ingestion_and_document_safety_spec.md`

## 1. Purpose

This document defines how the Nexa SaaS accepts user documents and converts them into safe product inputs.

Its purpose is to fix:
- how files enter the system,
- why uploaded files are treated as untrusted,
- how quarantine and scanning work,
- when a file becomes eligible for execution,
- which extraction limits apply,
- and how rejection, cleanup, and auditability behave.

## 2. Trust model

Every uploaded file is untrusted until proven safe.

This rule is mandatory.
The SaaS must not treat:
- successful upload,
- correct extension,
- or correct MIME type

as proof that a file is safe to use.

## 3. Upload architecture

The baseline SaaS uses a direct-to-object-storage upload model:

1. client asks for upload authorization,
2. server returns a presigned upload target,
3. browser uploads directly to object storage,
4. client confirms upload,
5. server begins scan/quarantine processing,
6. client polls upload status,
7. only safe files become usable for execution.

This architecture exists to avoid routing large file bodies through the application server.

## 4. Upload state machine

A valid file moves through the following states:

- `pending_upload`
- `quarantine`
- `scanning`
- `safe`
- `rejected`

### 4.1 Meaning of each state

- `pending_upload` — upload slot exists, file not yet confirmed usable
- `quarantine` — object exists but is still untrusted
- `scanning` — safety and/or extraction checks running
- `safe` — file may be referenced by runs
- `rejected` — file must not be used by any run

### 4.2 State transition audit

Every transition must be recorded in immutable audit rows.
Mutable current-state tables alone are not sufficient.

## 5. File-level safety

### 5.1 File-level safety is mandatory

The SaaS must perform file-level safety scanning before treating the file as a product input.

### 5.2 Text-level safety is not a substitute

Text-pattern scanning for PII or credential patterns does not replace:
- malware scanning,
- malformed document handling,
- or file trust checks.

The two layers solve different problems and both are required.

## 6. Accepted document types

The baseline SaaS accepts:
- PDF
- DOCX

Other document types are outside the baseline unless explicitly added later.

## 7. Safety scanning baseline

The baseline safety path includes:
- malware scanning,
- MIME / magic-byte coherence checking,
- parser failure handling,
- extraction timeout handling,
- and rejection with explicit reason codes.

The product should be able to tell the user:
- not only that a file failed,
- but why it failed in a machine-readable and UI-translatable way.

## 8. Extraction limits

The baseline SaaS must impose bounded extraction limits.

At minimum it must enforce boundedness over:
- file size,
- extraction time,
- PDF page count,
- DOCX structure depth or paragraph count,
- and maximum extracted character volume.

These limits exist to protect:
- cost,
- latency,
- worker health,
- and parser stability.

## 9. Rejection behavior

A rejected file must:
- remain unusable for runs,
- have a reason code,
- be represented in audit history,
- and be cleaned up according to lifecycle policy.

A rejection is not silent.
It is an explicit product state.

## 10. Safe-file rule for execution

Public run submission may reference only files whose upload state is `safe`.

A file in:
- `pending_upload`,
- `quarantine`,
- `scanning`,
- or `rejected`

must not be accepted as an execution input.

## 11. Storage roles for file data

The SaaS must distinguish:
- object bytes in object storage,
- upload metadata in Postgres,
- state transition audit rows,
- and extracted text or references used later in execution.

These are related but distinct artifacts.

## 12. Extracted text and document trust

A file becoming `safe` means the object is allowed into the product’s execution path.
It does not mean the text is intrinsically harmless.

After extraction:
- input safety rules still apply,
- credential/PII detection may still warn or block,
- and downstream product logic must continue to treat user content as sensitive.

## 13. Cleanup and lifecycle

The system must define lifecycle handling for:
- rejected uploads,
- expired unconfirmed uploads,
- safe uploads whose related run or account is removed,
- and orphaned stored objects.

The important rule is that object storage must not silently accumulate abandoned or unsafe data forever.

## 14. User experience requirements

The web product must surface upload states clearly enough that a non-technical user can tell:

- whether the file is still uploading,
- whether it is being scanned,
- whether it is ready,
- or whether it was rejected.

Users must not be asked to infer backend safety state indirectly.

## 15. Audit requirements

At minimum, audit must preserve:
- state transitions,
- rejection reasons,
- timestamps,
- and enough identifiers to reconstruct what happened without exposing document content.

## 16. Non-goals

This document does not define:
- OCR as a baseline requirement for browser SaaS,
- broad file-format support,
- public document sharing,
- collaborative annotation,
- or rich document rendering.

## 17. Acceptance criteria

This specification is satisfied only if all of the following are true:

1. files enter through a bounded, explicit upload architecture,
2. every file starts untrusted,
3. every file must pass through quarantine and scanning before use,
4. only `safe` files may be used for runs,
5. rejection is explicit, auditable, and user-visible,
6. extraction is bounded,
7. text-level safety does not replace file-level safety,
8. and lifecycle cleanup is defined for unsafe or expired objects.
