# Plugin Failure / Recovery Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_failure_recovery_contract.md`

## 1. Purpose

This document defines the canonical failure and recovery contract for plugins in Nexa.

It establishes:
- what counts as plugin execution failure
- how failure categories are classified
- how retryable and non-retryable failures differ
- how partial outcomes are handled
- how recovery attempts are performed and recorded
- how escalation, suspension, and deactivation rules operate
- how failure truth is preserved in trace, runtime state, and artifact relationships

## 2. Core Decision

1. Plugin failure must be explicit engine truth.
2. Failure must be categorized, not treated as one generic error.
3. Retry and recovery must be governed by policy and runtime rules.
4. Partial output may exist, but must remain distinguishable from final success.
5. Recovery attempts must be observable and historically traceable.
6. Severe or repeated failures may change plugin activation posture.

## 3. Non-Negotiable Boundaries

- Node boundary
- Working Context boundary
- Executor boundary
- Policy boundary
- Trace boundary

## 4. Core Vocabulary

- Failure
- Retryable Failure
- Non-Retryable Failure
- Recovery Attempt
- Escalation
- Posture Change

## 5. Canonical Lifecycle Position

PluginExecutionInstance
-> Failure Detection
-> Failure Classification
-> Partial Outcome Evaluation
-> Retry / Recovery Decision
-> Recovery Attempt or Escalation
-> Final Execution Outcome
-> Possible Plugin Posture Change

## 6. Canonical Failure State Object

PluginFailureState
- failure_state_id: string
- execution_instance_ref: string
- binding_ref: string
- plugin_id: string
- failure_category: enum(
    "input_failure",
    "policy_failure",
    "executor_failure",
    "output_failure",
    "artifact_failure",
    "timeout",
    "cancellation",
    "dependency_failure",
    "external_target_failure",
    "runtime_failure",
    "unknown_failure"
  )
- retryability: enum("retryable", "not_retryable", "requires_review")
- severity: enum("warning", "blocking", "critical")
- failure_code: string
- failure_message: string
- partial_output_present: bool
- artifact_partial_present: bool
- context_partial_present: bool
- escalation_required: bool
- notes: string | null

## 7. Canonical Recovery State Object

PluginRecoveryState
- recovery_state_id: string
- failure_state_ref: string
- recovery_policy_ref: string | null
- recovery_action: enum(
    "retry_same_binding",
    "retry_with_clean_context_slice",
    "retry_with_backoff",
    "skip_and_continue",
    "escalate",
    "suspend_plugin",
    "deactivate_plugin",
    "abort_node_execution"
  )
- recovery_attempt_count: int
- recovery_status: enum("not_attempted", "attempted", "succeeded", "failed", "escalated")
- final_outcome_ref: string | null
- notes: string | null

## 8. Canonical Failure Categories

- input_failure
- policy_failure
- executor_failure
- output_failure
- artifact_failure
- timeout
- cancellation
- dependency_failure
- external_target_failure
- runtime_failure
- unknown_failure

## 9. Retryability Rules

Usually retryable:
- transient dependency failure
- external target failure
- timeout under bounded retry policy
- transient executor failure

Usually not retryable:
- policy failure
- undeclared write attempt
- malformed required input
- disallowed external side effect
- structurally incompatible output shape

Requires review when retry policy cannot decide safely.

## 10. Partial Outcome Rules

Runtime must distinguish:
- no useful output
- partial context output only
- partial artifact output only
- both partial context and artifact output
- final output absent but intermediate output present

Partial outcomes must never be silently upgraded to final success.

## 11. Timeout and Cancellation Rules

Timeout must be evaluated against bound runtime constraints. Cancellation is a terminal execution outcome that must be recorded explicitly.

## 12. Recovery Actions

Supported bounded actions may include:
- retry same binding
- retry with clean context slice
- retry with backoff
- skip and continue
- escalate
- suspend plugin
- deactivate plugin
- abort node execution

## 13. Escalation Rules

Escalation is required when:
- retry policy cannot decide safely
- repeated failure exceeds threshold
- failure indicates policy/governance concern
- side effects may have partially occurred and require review
- runtime posture should not be changed automatically without review

## 14. Repeated Failure and Posture Change

Runtime may change plugin posture based on repeated failure history, e.g.:
- active -> suspended
- bound_ready -> bound_suspended
- installed active plugin -> deactivated in current runtime

## 15. Trace and Audit Requirements

The system must record:
- failure detection
- failure classification
- retry decision
- recovery attempt
- escalation event
- final recovery outcome
- posture change if any

## 16. Canonical Findings Categories

Examples:
- FAILURE_INPUT_REQUIRED_MISSING
- FAILURE_POLICY_BLOCKED
- FAILURE_EXECUTOR_ERROR
- FAILURE_OUTPUT_INVALID
- FAILURE_TIMEOUT
- FAILURE_CANCELLED
- RECOVERY_RETRY_SUCCEEDED
- RECOVERY_ESCALATED
- RECOVERY_PLUGIN_SUSPENDED
- RECOVERY_PLUGIN_DEACTIVATED

## 17. Explicitly Forbidden Patterns

- silent failure disappearance
- retry without category awareness
- partial-success masquerading
- policy-bypass recovery
- hidden suspension
- artifact/context ambiguity

## 18. Canonical Summary

- Plugin failure is explicit execution truth.
- Failure must be categorized, not flattened into generic error state.
- Retry and recovery must be bounded and policy-aware.
- Partial outcomes must remain distinguishable from final success.
- Repeated or severe failures may change plugin runtime posture.

## 19. Final Statement

A plugin in Nexa should not fail as anonymous broken code and should not recover through hidden guesswork.

It should fail explicitly, recover only through governed rules, and leave a clear historical record of what happened.

That is the canonical meaning of Plugin Failure / Recovery in Nexa.
