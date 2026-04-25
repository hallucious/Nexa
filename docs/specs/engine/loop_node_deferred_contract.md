# Loop Node Deferred Contract v0.1

## Recommended save path
`docs/specs/engine/loop_node_deferred_contract.md`

## 1. Status

Deferred.

This document is a preservation contract, not an active implementation contract.

## 2. Purpose

This document defines the future shape and boundaries of an explicit LoopNode in Nexa.

It exists so that loop support is not later implemented as raw cyclic graph edges or hidden repeated execution.

## 3. Core Decision

Looping must be explicit and bounded.

Official rule:

- raw graph cycles are invalid
- a loop must be represented by an explicit LoopNode or equivalent bounded control node
- every loop must declare termination, quota, trace, and artifact policy
- unbounded loops are forbidden

## 4. Non-Negotiable Boundaries

A LoopNode must not:

- redefine Circuit as an execution unit
- make the scheduler cyclic
- bypass validation
- hide iteration count
- mutate graph structure during execution
- silently carry state across iterations without policy
- silently carry state across runs
- create unbounded external side effects

## 5. Draft Canonical Shape

Future shape, not currently executable:

    node_id: string
    kind: "loop"
    label: optional string
    execution:
      loop:
        loop_body_ref: child circuit ref or bounded body ref
        input_mapping: object
        output_binding: object
        max_iterations: integer
        stop_condition: object
        state_carry_policy: object
        per_iteration_artifact_policy: object
        per_iteration_trace_policy: object
        timeout_policy: object
        quota_policy: object
        failure_policy: object
        cancellation_policy: optional object

## 6. Required Policies

### 6.1 max_iterations

Every loop must declare a maximum iteration count.

No implicit infinite loops.

### 6.2 stop_condition

Every loop must declare how it stops.

Examples:

- stop when verifier passes
- stop when output schema is satisfied
- stop when score threshold reached
- stop when max_iterations reached
- stop when human decision terminates loop

### 6.3 state_carry_policy

Every loop must declare what state carries from one iteration to the next.

Possible future values:

- none
- selected_context_keys
- previous_output_only
- accumulated_summary
- explicit_iteration_state_object

### 6.4 per_iteration_artifact_policy

Every loop must declare whether artifacts are:

- kept per iteration
- summarized
- final-only
- discarded only if policy permits and trace preserves evidence

### 6.5 failure_policy

Every loop must declare how failures are handled:

- fail_fast
- retry_iteration
- continue_with_warning
- return_best_effort_partial
- require_human_review

## 7. Loop Iteration Record

Each iteration must have a distinct record.

Minimum fields:

- loop_run_id
- parent_run_ref
- loop_node_ref
- iteration_index
- iteration_input_refs
- iteration_output_refs
- stop_condition_result
- iteration_status
- reason_code
- started_at
- completed_at
- artifact_refs
- trace_slice_ref

## 8. Streaming Loop Output Policy

Future loop streaming must distinguish:

- per-iteration stream chunks
- accumulated partial loop output
- final loop output
- stop-condition status
- iteration failure status

Rules:

1. A streamed iteration is not final loop completion.
2. Partial loop output must be labeled partial.
3. Final output may be emitted only after loop termination.
4. Cancellation must record whether current iteration was cancelled or the whole loop was cancelled.
5. UI must not fabricate progress beyond engine-emitted loop events.

## 9. Quota and Timeout Requirements

Loop execution must be quota-aware.

Minimum requirements:

- per-iteration cost tracking
- aggregate loop cost tracking
- max iteration guard
- timeout guard
- launch-time quota feasibility check when possible
- mid-loop quota stop rule when configured

## 10. Replay Requirements

Loop replay must preserve:

- iteration count
- per-iteration inputs and outputs
- stop-condition evaluations
- carried state
- artifact refs
- failure and cancellation decisions

If a loop cannot be replayed deterministically, the trace must say why.

## 11. Validation Requirements

Future validators must reject:

- loop node used before feature activation
- missing max_iterations
- missing stop_condition
- missing state_carry_policy
- missing per_iteration_trace_policy
- missing quota or timeout policy
- raw cycle used instead of LoopNode
- unbounded external side effect loop
- loop body reference missing
- loop body recursion beyond allowed depth

Planned rule anchors may include:

- FLOW-007 unsupported loop node
- FLOW-012 missing loop termination policy
- FLOW-013 unbounded loop
- FLOW-014 invalid loop body reference
- FLOW-015 loop artifact policy missing

## 12. Final Statement

Loop support is valuable, but it is architecture-sensitive.

Until this contract is promoted, Nexa must reject raw cycles and must not simulate loops through hidden repeated node execution.
