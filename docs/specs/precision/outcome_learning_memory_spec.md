# Outcome Learning Memory Spec v0.1

## Recommended save path
`docs/specs/precision/outcome_learning_memory_spec.md`

## 1. Purpose

This document defines the official Outcome Learning Memory system for Nexa.

Its purpose is to retain reusable operational knowledge from prior executions, including:

- successful route patterns
- failed route patterns
- verifier failure signatures
- branch / merge outcomes
- prompt/provider/plugin fit patterns
- human intervention outcomes

This system enables Nexa to learn from prior runs without changing core contract truth during execution.

## 2. Core Decision

Outcome memory is execution-to-execution learning, not execution-time self-modification.

Official rule:

- memory is updated after execution or review cycles
- memory informs future decisions
- memory does not silently mutate canonical runtime contracts

## 3. Core Principles

1. memory stores operational patterns, not hidden truth overrides
2. memory entries are trace-linked
3. success and failure memory are both first-class
4. memory must remain queryable by reason_code and context
5. memory suggestions must remain explainable
6. memory may influence routing, verification, and designer proposals
7. memory updates must remain policy-bounded

## 4. Canonical Memory Families

### 4.1 Success Pattern Memory
Stores:
- good route choices
- good verifier combinations
- good prompt/provider/plugin fit
- stable low-cost high-quality patterns

### 4.2 Failure Pattern Memory
Stores:
- repeated reason_codes
- repeated failure clusters
- high-cost low-gain patterns
- unstable route patterns
- repeated human rejection patterns

### 4.3 Repair Pattern Memory
Stores:
- what fixes worked for what problem class
- what fixes over-corrected
- what fixes required human review

## 5. Canonical Memory Object

OutcomeMemoryEntry
- memory_id: string
- memory_type: enum("success", "failure", "repair", "human_decision")
- task_class: string
- context_signature: object
- pattern_summary: string
- linked_reason_codes: list[string]
- linked_route_refs: list[string]
- linked_verifier_refs: list[string]
- linked_trace_refs: list[string]
- linked_artifact_refs: list[string]
- outcome_label: string
- confidence: float
- reuse_policy: string
- created_at: string

## 6. Memory Usage Surfaces

Outcome memory may inform:

- route suggestions
- retry strategy suggestions
- verifier tightening suggestions
- branch policy suggestions
- designer proposal critique hints
- human review recommendations

Memory may not directly auto-commit structure.

## 7. Update Rules

Memory update should happen:

- after completed execution
- after verifier aggregation
- after human review if relevant
- after replay mutation analysis
- after post-run evaluation

Memory updates must remain append-only in meaning.

## 8. First Implementation Scope

The first implementation should support:

- success memory entry
- failure memory entry
- reason_code-indexed lookup
- task-class lookup
- route suggestion hint output
- verifier tightening hint output
- trace linkage

## 9. Non-Goals for v0.1

Not required initially:

- fully autonomous memory-driven architecture mutation
- hidden online self-rewrite during active execution
- infinite retention without governance
- universal semantic memory of everything produced

## 10. Final Decision

Outcome Learning Memory is the official cross-run learning layer for the precision track.

It allows Nexa to become:
historically informed

without becoming:
silently self-rewriting during execution
