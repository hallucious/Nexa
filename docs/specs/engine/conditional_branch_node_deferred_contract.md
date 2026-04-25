# Conditional Branch Node Deferred Contract v0.1

## Recommended save path
`docs/specs/engine/conditional_branch_node_deferred_contract.md`

## 1. Status

Deferred.

This document is a preservation contract, not an active implementation contract.

## 2. Purpose

This document defines the future shape and boundaries of an explicit ConditionalBranchNode in Nexa.

It exists so that conditional branching is not later implemented as ambiguous fan-out edges, hidden runtime logic, or dynamic graph mutation.

## 3. Core Decision

Conditional branching must be explicit.

Official rule:

- structural fan-out is allowed now
- conditional path selection is deferred
- future conditional path selection must happen through a declared branch control node or equivalent explicit contract
- branch decisions must be traceable and replay-compatible

## 4. Non-Negotiable Boundaries

A ConditionalBranchNode must not:

- redefine Node as the sole execution unit
- mutate graph structure at runtime
- hide skipped paths
- silently execute multiple exclusive branches
- fabricate branch decisions after execution
- convert Designer proposals into runtime branch choices without approval

## 5. Draft Canonical Shape

Future shape, not currently executable:

    node_id: string
    kind: "conditional_branch"
    label: optional string
    execution:
      conditional_branch:
        decision_input: context path or node output ref
        branches:
          - branch_id: string
            condition: declared predicate or decision value
            target: node_id or output binding ref
            priority: optional integer
        default_branch: optional branch_id
        multi_match_policy: enum("first_priority", "error", "all_matching")
        no_match_policy: enum("default", "skip", "error")
        decision_record_policy: object
        trace_policy: object

## 6. Branch Decision Record

A future branch decision must produce a machine-readable decision record.

Minimum fields:

- decision_id
- run_ref
- node_ref
- input_ref
- evaluated_value_summary
- matched_branch_ids
- selected_branch_id
- default_used
- no_match_result
- decision_reason_code
- timestamp
- deterministic_replay_hint

The decision record is execution evidence.
It is not approval truth.

## 7. Validation Requirements

Future validators must reject:

- branch node used before feature activation
- missing decision input
- branch target missing
- duplicate branch ids
- ambiguous multi-match policy
- no default branch when no-match policy requires default
- branch condition using unsupported predicate language
- branch node causing raw graph cycle
- branch side effects without policy

Planned rule anchors may include:

- FLOW-006 unsupported conditional branch node
- FLOW-009 invalid branch decision input
- FLOW-010 ambiguous branch selection policy
- FLOW-011 missing branch target

## 8. Trace Requirements

Trace must show:

- branch node started
- branch decision evaluated
- selected branch
- skipped branches
- default branch use, if any
- branch decision failure, if any

Trace must not imply that unselected exclusive branches executed.

## 9. Artifact Requirements

If branch decisions emit artifacts:

- they must be append-only
- they must be decision-scoped
- they must be linked to the branch node and run
- they must not rewrite upstream artifacts
- they must not be treated as final output unless explicitly bound

## 10. UI Requirements

UI must distinguish:

- structural fan-out
- conditional branch candidates
- selected branch
- skipped branch
- branch decision error

Beginner-facing UI may compress this into plain language, but engine truth must remain accessible after appropriate disclosure.

## 11. Final Statement

Conditional branching belongs in Nexa only as explicit, bounded, decision-recorded control flow.

Until this contract is promoted, multiple outgoing edges are structural fan-out only.
