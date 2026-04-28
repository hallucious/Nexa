# Operations Capability Levels and Permission Specification

## Recommended save path
`docs/specs/ops/ops_capability_levels_and_permission_spec.md`

## 1. Purpose

This document defines the capability levels and permission boundaries for Nexa's AI-assisted operations layer.

Its purpose is to ensure that operational assistance is useful without silently becoming uncontrolled operational authority.

## 2. Scope

This specification governs:

1. what the operations AI may read,
2. what it may recommend,
3. what it may execute directly,
4. what requires human approval,
5. what is forbidden from autonomous execution.

## 3. Core rule

The default rule is:

**The operations AI may read and recommend before it may act.**

Execution authority must be granted explicitly by capability level, not inferred from data access.

## 4. Capability levels

### 4.1 Level 1 — Read-only

Read-only capability allows the system to inspect operational state and produce summaries.

Permitted examples:

1. summarize failed runs,
2. summarize queue backlog,
3. summarize provider incidents,
4. summarize upload rejection patterns,
5. summarize quota anomalies,
6. summarize billing reconciliation failures,
7. summarize backup verification outcomes.

Read-only capability must not mutate any system of record.

### 4.2 Level 2 — Recommend-only

Recommend-only capability allows the system to produce ranked or structured operational suggestions.

Permitted examples:

1. recommend retry candidates,
2. recommend stuck-job reprocessing order,
3. recommend quarantine review priority,
4. recommend webhook replay candidates,
5. recommend plan-override review for support,
6. recommend runbook selection,
7. recommend incident severity.

Recommend-only capability must not execute the recommendation.

### 4.3 Level 3 — Safe-execute

Safe-execute capability allows a narrow, enumerated set of low-risk, reversible, or non-destructive actions.

Safe-execute is allowed only for actions that satisfy all of the following:

1. the action is scoped,
2. the action is reversible or harmless if repeated,
3. the action does not alter billing, authentication, quota policy, user data, or secrets,
4. the action is fully auditable,
5. the action can be disabled centrally.

Permitted examples:

1. trigger provider health probe,
2. refresh non-authoritative cache,
3. generate diagnostic evidence bundle,
4. launch safe cleanup job,
5. refresh derived operational summary.

### 4.4 Level 4 — Approval-required execute

This level allows the system to prepare and stage actions, but actual execution requires explicit human approval.

Examples:

1. retry failed run,
2. force-reset stuck run,
3. replay payment webhook,
4. apply temporary quota override,
5. override upload quarantine disposition,
6. trigger provider failover,
7. launch bounded recovery workflow.

Approval-required actions must state:

1. why the action is recommended,
2. what evidence supports it,
3. what could go wrong,
4. what rollback is available,
5. what approval level is required.

### 4.5 Level 5 — Forbidden autonomous actions

These actions must never execute autonomously.

Forbidden examples:

1. production database restore,
2. user deletion,
3. irreversible data purge outside explicit retention workflows,
4. billing correction or refund,
5. subscription plan mutation,
6. secret rotation,
7. auth mode change,
8. global quota policy change,
9. disabling observability, safety, or audit systems.

## 5. Permission classes

The operations system must separate permissions by class.

Minimum classes:

1. `read_state`
2. `read_redacted_evidence`
3. `recommend_action`
4. `execute_safe_action`
5. `stage_approval_required_action`
6. `execute_approved_action`
7. `forbidden_action`

No role may collapse all classes into one undifferentiated permission.

## 6. Permission inheritance rule

Read capability does not imply recommend capability.
Recommend capability does not imply execute capability.
Execute capability does not imply policy-authority capability.

Permission inheritance must be explicit and minimal.

## 7. Actor classes

The system must distinguish actors.

Minimum actor classes:

1. human operator,
2. AI assistant,
3. automation runtime,
4. approval authority.

The same physical system may host more than one actor class, but the audit model must keep them distinct.


## 7A. Product-user exclusion rule

General product users are not operations actors.

A general product user may own workspaces, create circuits, run workflows, upload files, view their own results, and manage ordinary product settings.
None of those product capabilities grants access to the AI-assisted operations system.

The following must be denied to general product users:

1. operations AI route access,
2. operations AI UI access,
3. operations AI summary access,
4. operations evidence bundle access,
5. operations recommendation access,
6. operations approval access,
7. operations action execution,
8. operations AI audit-log access.

The denial must happen at backend policy level.
The UI may hide these surfaces, but UI hiding is not the source of authority.

## 7B. Required actor-to-permission matrix

A conforming implementation must encode a matrix equivalent to the following.

| Actor class | Allowed AI-assisted operations capability | Notes |
|---|---|---|
| `general_user` | none | Product access only. No ops AI permission. |
| `support_limited` | delegated read-only or support-safe recommendation only | Must be explicitly granted and scope-limited. |
| `operator` | read-only and recommend-only by default | May stage actions only if explicitly granted. |
| `admin` | read, recommend, stage, approve admin-level actions | Still cannot bypass owner-level approvals. |
| `owner` | highest approval authority | Still subject to audit, policy, and forbidden-action rules. |
| `ops_ai_service` | no independent human authority | May act only under policy and recorded human/automation context. |
| `automation_runtime` | narrow whitelisted housekeeping only | No broad operational authority. |

The same authenticated account may have multiple roles, but every request must resolve to an explicit actor class and permission set before any operations AI work begins.

## 7C. Capability-to-route binding

Routes must declare required permissions explicitly.

Minimum route binding:

| Route class | Required permission |
|---|---|
| read summaries | `ops.read_summary` |
| read evidence bundles | `ops.read_evidence_redacted` |
| generate recommendations | `ops.recommend_action` |
| stage an action | `ops.stage_action` |
| approve support action | `ops.approve_support_action` |
| approve admin action | `ops.approve_admin_action` |
| approve owner-sensitive action | `ops.approve_owner_action` |
| execute approved action | `ops.execute_approved_action` |
| change operations policy | `ops.manage_ops_policy` |

No route may infer its authorization from UI state, frontend claims, workspace ownership, or generic authentication alone.

## 8. Approval mapping

Approval levels must be risk-based.

Minimum mapping:

1. support-level approval for bounded support actions,
2. admin-level approval for operational mutations,
3. owner-level approval for financially sensitive, data-sensitive, or recovery-sensitive actions.

## 9. Escalation rule

If the operations AI is uncertain which capability level applies, it must choose the safer level and escalate.

In uncertainty:
1. downgrade execution to recommendation,
2. request human review,
3. attach evidence,
4. refuse unsafe autonomous action.

## 10. Acceptance criteria

A conforming implementation satisfies this specification only if:

1. capability levels are explicit,
2. permission classes are explicit,
3. read/recommend/execute boundaries are not collapsed,
4. approval-required actions cannot bypass approval,
5. forbidden actions cannot be executed autonomously,
6. all capability use is auditable.
