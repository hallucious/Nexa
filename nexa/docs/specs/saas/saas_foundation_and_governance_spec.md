# Nexa SaaS Foundation and Governance Specification

Spec version: 1.0
Status: Approved baseline derived from `nexa_saas_completion_plan_v0.4.md`
Document type: Foundational SaaS specification
Authority scope: Cross-cutting SaaS governance, mutability, retention, and authority rules
Recommended path: `docs/specs/saas/saas_foundation_and_governance_spec.md`

## 1. Purpose

This document defines the foundational rules that the Nexa SaaS must obey before any feature-specific layer is considered valid.

Its purpose is to prevent later contradictions about:
- what the SaaS is,
- what the minimum viable SaaS milestone means,
- which state is authoritative,
- which data may be mutated or deleted,
- how GDPR interacts with immutable operational history,
- and which boundaries must remain stable as the SaaS grows.

This is the governance spine of the SaaS specification family.

## 2. Product definition

Nexa SaaS is the product form of Nexa in which:
- authenticated users access the system through the web,
- state is persisted in production-grade backends,
- document-based AI execution runs asynchronously,
- product value is delivered through templated use cases,
- usage is governed commercially and operationally,
- and the service can be observed, recovered, and supported safely.

The first intended user segment is:
- freelancers and sole proprietors,
- with contract review as the first killer use case.

## 3. Minimum SaaS milestones

### 3.1 Minimum viable SaaS

Minimum viable SaaS is reached when all of the following are true:

1. asynchronous execution exists,
2. document upload and safety scanning exist,
3. the contract review use case works end-to-end,
4. the product is accessible in a browser,
5. basic error visibility exists,
6. and core public-safety measures such as rate limiting and CORS restriction are active.

### 3.2 Revenue-generating SaaS

Revenue-generating SaaS is reached when all of the following are added:

1. billing,
2. quota enforcement,
3. provider operating model finalization,
4. backup running in production,
5. and notification delivery.

### 3.3 Operationally mature SaaS

Operational maturity is reached when all of the following are added:

1. full observability with redaction,
2. admin/support surface,
3. automated deployment,
4. and durable recovery/runbook coverage.

### 3.4 Full expansion

Full expansion is later than operational maturity and includes:
- progressive capability activation,
- mobile,
- and MCP.

## 4. Authoritative system hierarchy

The SaaS must treat not all systems as equal.
For each state class, one system is authoritative.

### 4.1 Authoritative state classes

| State class | Authoritative system | Why |
|---|---|---|
| Identity and authentication | Clerk | Clerk is the source of real identity and session validity |
| Workspace and product state | Postgres | Product state must be durable and queryable |
| Uploaded file object bytes | S3 | Object storage is authoritative for file bytes |
| Async job queue | Redis/arq | Queue state lives here, but only transiently |
| Billing truth | Stripe + reconciled Postgres | Stripe is the payment authority; Postgres reflects local product view |
| Observability | Sentry / OTel backend | Useful for diagnosis, not business truth |

### 4.2 Recovery direction rule

During incident recovery, the authoritative system for the relevant state class must be restored or reconciled first.
Derived systems are rebuilt from authoritative systems, never the other way around.

## 5. Table mutability categories

Every table must belong to exactly one category.

### 5.1 Category A — Immutable append-only

Definition:
- rows are never updated,
- rows are never deleted,
- new state is represented only by additional rows,
- and there are no exceptions for retention, GDPR, or operator action.

Examples:
- `execution_record`
- `file_upload_events`
- `run_action_log`
- `execution_record_archive_index`
- `execution_retention_audit`
- `admin_action_audit`
- `user_deletion_audit`

### 5.2 Category B — Mutable state

Definition:
- rows represent current state,
- updates are expected and legitimate,
- and rows may be deleted as part of user deletion or state turnover.

Examples:
- `workspaces`
- `workspace_memberships`
- `provider_bindings`
- `user_subscriptions`
- `file_uploads`
- `user_preferences`
- `push_notification_tokens`

### 5.3 Category C — TTL-bounded deletable

Definition:
- rows are temporary operational state,
- rows expire after a bounded window,
- rows are deleted by cleanup jobs after their usefulness ends.

Examples:
- `run_submission_dedupe`
- `run_submissions`
- `quota_usage`

### 5.4 Category D — Permanent audit

Definition:
- rows are never deleted for any reason,
- rows are also immutable append-only,
- and even operator-driven cleanup must not remove them.

Examples:
- `admin_action_audit`
- `user_deletion_audit`
- `execution_retention_audit`
- `file_upload_events`

## 6. PII placement rule

Immutable append-only tables must not store directly mutable personal identity fields.

### 6.1 Forbidden in Category A tables

The following must not appear directly in Category A rows:
- raw user id,
- email address,
- display name,
- IP address,
- Clerk subject,
- payment customer identifiers that would require later mutation,
- or any field whose later removal would require an UPDATE.

### 6.2 Allowed identity linkage form

Category A tables may store only opaque references such as:
- `user_ref`,
- a one-way hash of internal user identity,
- or other non-reversible identifiers approved by privacy policy.

### 6.3 Consequence for GDPR

GDPR deletion must operate on:
- Clerk identity,
- mutable user-linked tables,
- file objects in S3,
- and other deletable references,

but must not mutate immutable operational history.

## 7. Immutable execution-history rule

### 7.1 Execution records are permanent

`execution_record` is immutable and non-deletable.

It is not:
- soft-deleted,
- anonymized in place,
- or hard-deleted later.

### 7.2 How archival works

Archival is handled through:
- archive index tables,
- read-surface filtering,
- and storage-tiering or export strategies outside the row itself.

### 7.3 Why this matters

Execution history is one of the most trust-sensitive layers in Nexa.
If it can be silently rewritten or removed, the product loses forensic trust, operational trust, and governance clarity.

## 8. GDPR interaction model

### 8.1 What gets deleted or anonymized

User deletion must remove or sever:
- Clerk identity,
- mutable workspace membership linkage,
- mutable subscription state,
- mutable user preferences,
- and uploaded file objects.

### 8.2 What does not change

Immutable operational history does not change.
Instead, it becomes permanently detached from real user identity because only opaque references remain.

### 8.3 Compliance model

The SaaS compliance model depends on the product never storing direct PII inside immutable execution history.
That is the enabling rule that makes both privacy and immutability possible at the same time.

## 9. Planning and specification authority

This specification family is downstream of the approved SaaS completion plan, but upstream of implementation plans.

### 9.1 If a plan and a spec differ

Behavior and governance are governed by the spec.
Execution order and file-level work partitioning are governed by implementation plans.

### 9.2 If a future feature conflicts with this document

The feature must either:
1. comply with this document, or
2. trigger an explicit revision of this document.

Silent exceptions are forbidden.

## 10. Cross-layer product rules

The SaaS product must preserve these overall rules:

1. the user-visible product must never redefine core Nexa execution truth,
2. economic rules must not override safety rules,
3. recovery rules must not break append-only guarantees,
4. convenience must not defeat auditability,
5. and product expansion must not outrun operational maturity.

## 11. Deferred domains

This foundational document does not define:
- visual graph editing,
- team collaboration,
- enterprise policy controls,
- self-hosted packaging,
- or AI-assisted operations.

Those may depend on this document, but are not defined by it.

## 12. Acceptance criteria

This document is satisfied only if the SaaS interpretation remains internally consistent on:

1. milestone meaning,
2. source-of-truth hierarchy,
3. table mutability categories,
4. PII placement,
5. immutable execution history,
6. and GDPR handling.

If any later document reintroduces contradiction between those six items, this document has been violated.
