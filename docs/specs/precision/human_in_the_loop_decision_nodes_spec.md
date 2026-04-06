# Human-in-the-Loop Decision Nodes Spec v0.1

## Recommended save path
`docs/specs/precision/human_in_the_loop_decision_nodes_spec.md`

## 1. Purpose

This document defines the official Human-in-the-Loop Decision Node system for Nexa.

Its purpose is to provide explicit human intervention points without collapsing engine ownership or traceability.

This system supports:
- approval
- feedback
- revision request
- reject / escalate
- human-grounded merge or route choice

## 2. Core Decision

Human intervention must be explicit, bounded, and traceable.

Official rule:

- human intervention is a node-level or gate-level event
- human decisions are recorded as structured operational truth
- human intervention may steer execution, but does not erase prior machine state

## 3. Core Principles

1. human intervention is explicit
2. human decision reasons are recorded
3. approval and rejection are distinct
4. revision requests remain traceable
5. human intervention does not silently rewrite history
6. execution may pause for review
7. policy may require human review

## 4. Canonical Human Decision Types

- approve
- reject
- request_revision
- choose_branch
- choose_merge
- override_with_reason
- stop_execution

## 5. Canonical Result Object

HumanDecisionRecord
- decision_id: string
- target_ref: string
- decision_type: string
- actor_ref: string
- rationale_text: optional string
- selected_option_ref: optional string
- timestamp: string
- downstream_action: enum("continue", "rerun", "branch", "merge", "stop", "escalate")
- trace_refs: list[string]

## 6. Human Review Trigger Conditions

Human review may be triggered by:

- policy gate
- low-confidence threshold
- repeated verifier failure
- high-impact merge conflict
- high-risk external action
- user-configured mandatory review stage

## 7. Execution Rules

A human-in-the-loop node or gate must support:

- pause state
- preview surface
- visible pending-review status
- recorded decision
- bounded resume path

The engine, not the UI, owns the pending-review truth.

## 8. First Implementation Scope

The first implementation should support:

- approve / reject / request_revision
- pause-for-review event
- preview linkage
- structured decision record
- resume / rerun / stop actions
- trace persistence

## 9. Non-Goals for v0.1

Not required initially:

- full collaborative multi-user workflow system
- unrestricted in-place manual structural editing as truth source
- UI-only fake approval states
- silent approval via default timeout

## 10. Final Decision

Human-in-the-Loop Decision Nodes are the official intervention boundary of the precision track.

They ensure Nexa remains:
automatable but governable

instead of:
fully automatic but operationally unaccountable
