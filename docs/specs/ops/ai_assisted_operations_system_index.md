# AI-Assisted Operations System Specification Index

## Recommended save path
`docs/specs/ops/ai_assisted_operations_system_index.md`

## 1. Purpose

This document is the index for the AI-assisted operations specification family.

Its purpose is to split the operational-assistance domain into stable, independent specification documents so that:

1. each operational concern can evolve independently,
2. implementation planning can reference a smaller and clearer authority surface,
3. future AI systems can consume a structured specification family rather than one oversized document.

This index is the entry point for the AI-assisted operations specification set.

## 2. Scope

This index governs the specification family for Nexa's AI-assisted operations layer.

It covers:

1. capability levels and permission boundaries,
2. data-source access rules,
3. redaction and sensitive-data handling,
4. decision outputs and runbook integration,
5. audit and approval workflow,
6. automation boundaries and action execution,
7. multi-agent coordination,
8. failure modes and safety controls,
9. rollout stages and acceptance criteria.

This index does not define product-user functionality.
It defines the operational-assistance specification family only.

## 3. Relationship to the product

The AI-assisted operations layer is downstream of the product runtime and operational surfaces.


### 3.5 Internal access boundary

The entire AI-assisted operations specification family is governed by one cross-cutting rule:

AI-assisted operations is internal owner/operator/admin infrastructure.
It is not a general-user product feature.

General users must not access operations AI routes, summaries, evidence bundles, recommendations, approvals, action execution, or audit records.
This must be enforced by backend authorization and policy checks, not merely by hidden UI navigation.

It depends on:

1. the product's run state,
2. queue and worker state,
3. provider health,
4. upload safety state,
5. billing and quota state,
6. admin and support APIs,
7. audit logs,
8. observability outputs,
9. runbooks,
10. backup and recovery state.

It must not redefine those systems.
It must consume and operate through them.

## 4. Document family

The specification family consists of the following documents.

### 4.1 Capability and permission specification
`docs/specs/ops/ops_capability_levels_and_permission_spec.md`

Defines:
1. read-only capability,
2. recommend-only capability,
3. safe-execute capability,
4. approval-required execute capability,
5. forbidden autonomous actions,
6. permission-boundary rules.

### 4.2 Data-source and access-control specification
`docs/specs/ops/ops_data_source_and_access_control_spec.md`

Defines:
1. operational data sources,
2. source tiers,
3. allowed and forbidden access paths,
4. freshness and consistency expectations,
5. evidence-bundle construction rules.

### 4.3 Redaction and sensitive-data handling specification
`docs/specs/ops/ops_redaction_and_sensitive_data_handling_spec.md`

Defines:
1. sensitive-data classes,
2. redaction requirements,
3. allowed diagnostic transforms,
4. model input restrictions,
5. privacy-preserving evidence rules.

### 4.4 Decision output and runbook integration specification
`docs/specs/ops/ops_decision_output_and_runbook_integration_spec.md`

Defines:
1. machine-readable operational outputs,
2. severity and confidence structure,
3. runbook linking rules,
4. evidence presentation,
5. response-shaping rules for operators.

### 4.5 Audit and approval workflow specification
`docs/specs/ops/ops_audit_and_approval_workflow_spec.md`

Defines:
1. audit event structure,
2. approval levels,
3. recommendation versus execution separation,
4. operator confirmation requirements,
5. audit retention obligations.

### 4.6 Automation boundary and action execution specification
`docs/specs/ops/ops_automation_boundary_and_action_execution_spec.md`

Defines:
1. what may be fully automated,
2. what may be semi-automated,
3. what remains manual-only,
4. execution gating,
5. rollback expectations.

### 4.7 Multi-agent coordination specification
`docs/specs/ops/ops_multi_agent_coordination_spec.md`

Defines:
1. role separation across multiple AI systems,
2. handoff contracts,
3. trust-tier separation,
4. evidence passing,
5. coordination failure handling.

### 4.8 Failure mode and safety control specification
`docs/specs/ops/ops_failure_mode_and_safety_control_spec.md`

Defines:
1. operations-AI failure classes,
2. mitigation controls,
3. degraded-mode behavior,
4. recommendation confidence limits,
5. fail-safe defaults.

### 4.9 Rollout and acceptance specification
`docs/specs/ops/ops_rollout_and_acceptance_spec.md`

Defines:
1. staged rollout,
2. preconditions for each stage,
3. acceptance criteria,
4. rollback criteria,
5. production-readiness thresholds.

## 5. Reading order

Read in this order:

1. this index,
2. capability and permission,
3. data-source and access-control,
4. redaction and sensitive-data handling,
5. decision output and runbook integration,
6. audit and approval workflow,
7. automation boundary and action execution,
8. multi-agent coordination,
9. failure mode and safety control,
10. rollout and acceptance.

## 6. Authority rule

If two documents in this family appear to conflict:

1. capability and permission rules override convenience,
2. redaction and sensitive-data handling rules override diagnostic convenience,
3. audit and approval rules override automation convenience,
4. failure and safety rules override aggressive autonomy,
5. rollout and acceptance rules govern whether a stage is permitted to advance.

## 7. Maintenance rule

Any implementation change that alters:

1. capability levels,
2. data access,
3. redaction behavior,
4. approval workflow,
5. automation boundaries,
6. multi-agent coordination rules,
7. safety controls,
8. rollout criteria,

must update the affected spec document in the same change batch.

## 8. Final rule

This specification family defines how Nexa's AI-assisted operations layer may assist operators.

It does not authorize unrestricted operational autonomy.
