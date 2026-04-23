# Operations Rollout and Acceptance Specification

## Recommended save path
`docs/specs/ops/ops_rollout_and_acceptance_spec.md`

## 1. Purpose

This document defines the staged rollout path and acceptance criteria for Nexa's AI-assisted operations layer.

## 2. Scope

This specification governs:

1. rollout stages,
2. preconditions,
3. advancement criteria,
4. rollback criteria,
5. production-readiness thresholds.

## 3. Rollout rule

The operations AI layer must be introduced in stages.

Broad autonomous operational action is forbidden as an initial rollout mode.

## 4. Stage definitions

### 4.1 Stage 1 — Read-only summarization

Capabilities:

1. summarize failed runs,
2. summarize queue backlog,
3. summarize provider issues,
4. summarize quota and billing anomalies,
5. link runbooks.

Preconditions:

1. operational source surfaces exist,
2. redaction surfaces exist,
3. audit path for recommendations exists.

Advancement requires:
1. summaries are useful,
2. no sensitive-data leakage,
3. operator trust is improving without over-trust.

### 4.2 Stage 2 — Recommendation engine

Capabilities:

1. recommend actions,
2. rank incidents,
3. prepare evidence bundles,
4. recommend runbooks and next steps.

Preconditions:

1. Stage 1 stable,
2. structured output schema in place,
3. evidence bundles reliable,
4. confidence labeling in place.

Advancement requires:
1. recommendation precision is acceptable,
2. operators can reject poor recommendations easily,
3. audit separation between recommendation and execution is proven.

### 4.3 Stage 3 — Approval-gated execution

Capabilities:

1. stage safe or bounded actions,
2. execute them after approval,
3. audit approval and execution separately.

Preconditions:

1. approval workflow implemented,
2. action gating implemented,
3. rollback or compensating action documented where applicable.

Advancement requires:
1. approvals are respected,
2. no bypass paths exist,
3. operators can inspect evidence before approving.

### 4.4 Stage 4 — Narrow autonomous housekeeping

Capabilities:

1. safe cleanup,
2. safe health probes,
3. routine report generation,
4. low-risk maintenance only.

Preconditions:

1. Stages 1–3 stable,
2. safe-execute action set explicitly whitelisted,
3. audit and redaction systems proven reliable.

Advancement beyond this stage requires a separate decision.

## 5. Rollback criteria

A stage must roll back or pause if any of the following occur:

1. sensitive-data leakage,
2. approval bypass,
3. unsafe recommendation trend,
4. operator confusion or over-trust becomes operationally material,
5. audit trail gaps appear,
6. degraded-mode handling fails,
7. automation attempts action outside its allowed category.

## 6. Production-readiness thresholds

Before production exposure beyond read-only summarization, the system should demonstrate:

1. stable redaction behavior,
2. reliable evidence bundling,
3. explicit approval workflow,
4. working audit capture,
5. clear operator UX,
6. rollback playbooks for the ops AI layer itself.

## 7. Acceptance criteria

A conforming rollout satisfies this specification only if:

1. rollout is staged,
2. each stage has explicit preconditions,
3. each stage has explicit advancement criteria,
4. rollback criteria are explicit,
5. broad autonomous operation is not treated as the default success state.
