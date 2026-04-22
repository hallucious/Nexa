# Operations Data Source and Access Control Specification

## Recommended save path
`docs/specs/ops/ops_data_source_and_access_control_spec.md`

## 1. Purpose

This document defines what operational data the AI-assisted operations layer may consume, how that data is classified, and what access controls apply.

## 2. Scope

This specification governs:

1. operational data source classes,
2. source trust and freshness tiers,
3. evidence-bundle construction,
4. forbidden access paths,
5. consistency expectations.

## 3. Source classes

Minimum operational source classes:

1. run state and execution records,
2. queue and worker state,
3. provider health and probe history,
4. upload quarantine and file-safety state,
5. quota and billing state,
6. admin and audit logs,
7. observability summaries,
8. backup and recovery state,
9. configuration validation state,
10. runbook metadata.

## 4. Source tiers

### 4.1 Tier 1 — System-of-record sources

These are authoritative sources.

Examples:

1. Postgres-backed execution records,
2. quota usage records,
3. subscription records,
4. upload state records,
5. audit log records.

Tier 1 sources are preferred whenever a recommendation or action decision is made.

### 4.2 Tier 2 — Operational derived sources

These are useful, but derived from authoritative state.

Examples:

1. queue projections,
2. recent-activity aggregations,
3. observability summaries,
4. provider health snapshots,
5. backup verification summaries.

Tier 2 sources may be used for triage but should link back to Tier 1 evidence where available.

### 4.3 Tier 3 — Ephemeral runtime sources

These are non-authoritative and may be stale.

Examples:

1. cache entries,
2. transient in-memory projections,
3. unstable worker-local summaries.

Tier 3 data must not be used as sole justification for a risky action.

## 5. Freshness rules

Each recommendation must carry freshness expectations for its evidence bundle.

Minimum freshness labels:

1. `live`
2. `recent`
3. `stale`
4. `unknown`

If source freshness is stale or unknown, the system must state that uncertainty.

## 6. Evidence bundle construction

Every meaningful recommendation must be attached to an evidence bundle.

An evidence bundle must contain:

1. source references,
2. source timestamps,
3. source tiers,
4. source freshness labels,
5. summary fields,
6. redaction status.

The evidence bundle must be sufficient for an operator to verify the recommendation without guessing where the information came from.

## 7. Forbidden access patterns

The operations AI must not read from the following unless separately approved under a stricter policy:

1. raw confidential document content,
2. prompt-rendered user content,
3. unrestricted provider outputs,
4. raw secret values,
5. raw JWT values,
6. presigned URLs,
7. direct unmanaged access to production data stores outside approved access surfaces.

The system must consume structured and redacted operational surfaces instead of unrestricted raw data pulls.

## 8. Consistency rule

If two source tiers disagree:

1. Tier 1 overrides Tier 2 and Tier 3,
2. Tier 2 overrides Tier 3,
3. the disagreement itself must be surfaced if operationally relevant.

The system must not silently merge contradictory sources into a confident recommendation.

## 9. Minimal source set for action recommendation

No execution-affecting recommendation may be produced without at least:

1. one Tier 1 or Tier 2 source,
2. explicit freshness labels,
3. target scope identification,
4. linked runbook or policy reference.

## 10. Acceptance criteria

A conforming implementation satisfies this specification only if:

1. operational sources are classified,
2. source-tier handling is explicit,
3. evidence bundles are structured,
4. stale or uncertain data is labeled,
5. forbidden raw data paths are not used,
6. risky recommendations are not based solely on ephemeral state.
