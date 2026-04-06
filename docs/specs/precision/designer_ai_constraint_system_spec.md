# Designer AI Constraint System Spec v0.1

## Recommended save path
`docs/specs/precision/designer_ai_constraint_system_spec.md`

## 1. Purpose

This document defines the official Designer AI Constraint System for Nexa.

Its purpose is to constrain Designer AI so that circuit generation and modification remain:

- bounded
- reviewable
- lintable
- simulation-checkable
- aligned with engine contracts

This system reduces structural hallucination.

## 2. Core Decision

Designer AI may propose structure, but must do so under explicit constraints.

Official rule:

- Designer AI does not freely invent runtime truth
- Designer AI proposals must pass rule DSL, lint, critique, and preview boundaries
- ambiguity must remain visible

## 3. Core Principles

1. Designer AI remains proposal-producing
2. allowed node/resource types are explicit
3. forbidden patterns are explicit
4. generation rules are machine-checkable
5. generated structures must be lintable
6. generated structures should be sample-simulatable before commit
7. auto-critique must not bypass human approval

## 4. Constraint System Components

### 4.1 Constraint DSL
Defines:
- allowed node kinds
- allowed resource combinations
- mandatory verifier rules
- forbidden structural patterns
- required output bindings
- maximum complexity and depth

### 4.2 Circuit Lint
Checks:
- missing required outputs
- dead-end nodes
- ambiguous branch closure
- pipeline collapse risk
- missing verification on high-risk paths
- invalid resource coupling

### 4.3 Auto-Critique
Designer proposals should be critiqued before review.

Checks:
- whether proposal matches user request
- whether proposal is overbuilt
- whether proposal violates existing invariants
- whether safer narrower alternatives exist

### 4.4 Sample Simulation
For selected proposal classes, Nexa should support:
- mock input dry-run
- contract-only simulation
- structural outcome preview

## 5. Canonical Constraint Objects

DesignerConstraintPolicy
- policy_id: string
- allowed_node_kinds: list[string]
- allowed_resource_types: list[string]
- forbidden_patterns: list[string]
- required_patterns: list[string]
- max_node_count: int
- max_depth: int
- mandatory_review_conditions: list[string]

DesignerLintReport
- report_id
- target_ref
- blocking_findings
- warning_findings
- recommended_repairs
- explanation

DesignerCritiqueReport
- critique_id
- proposal_ref
- fidelity_to_request
- overbuild_risk
- invariant_risk
- safer_alternative_notes
- explanation

## 6. First Implementation Scope

The first implementation should support:

- allowed node kind list
- forbidden pattern list
- basic lint report
- pre-review auto-critique
- contract-only dry-run
- complexity cap enforcement

## 7. Non-Goals for v0.1

Not required initially:

- unrestricted free-form agentic circuit synthesis
- self-expanding grammar
- direct commit from auto-generated draft
- hidden repair of structurally invalid proposals

## 8. Final Decision

The Designer AI Constraint System is the official anti-structural-hallucination layer for Nexa.

It ensures Designer AI behaves like:
a bounded design assistant

not:
an unbounded runtime re-architect
