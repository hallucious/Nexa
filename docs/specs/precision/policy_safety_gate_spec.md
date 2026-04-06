# Policy / Safety Gate Spec v0.1

## Recommended save path
`docs/specs/precision/policy_safety_gate_spec.md`

## 1. Purpose

This document defines the official Policy / Safety Gate for Nexa.

Its purpose is to classify risk, enforce restrictions, and block unsafe actions before they become trusted execution outcomes.

This layer is commercial-trust critical.

## 2. Core Decision

Nexa must not treat safety as an optional downstream explanation.

Official rule:

- risk classification must happen explicitly
- permission boundaries must be enforceable
- blocked actions must remain blocked even if they seem operationally convenient

## 3. Core Principles

1. safety is engine-owned
2. policy and permission checks are explicit
3. restricted actions remain visible, not silently hidden
4. policy veto dominates quality convenience
5. tool/plugin permissions must be scoped
6. human approval may be mandatory for specific risk tiers
7. safety logs must remain traceable

## 4. Risk Tiers

Minimum risk tiers:

- `low`
- `medium`
- `high`
- `restricted`
- `blocked`

Risk tier may depend on:
- request content
- target action
- tool/plugin capability
- data sensitivity
- user / workflow policy
- repeated failure / abuse patterns

## 5. Canonical Result Object

SafetyGateResult
- gate_id: string
- target_ref: string
- risk_tier: string
- status: enum("allow", "allow_with_review", "restrict", "block")
- reason_codes: list[string]
- blocked_actions: list[string]
- allowed_actions: list[string]
- required_reviews: list[string]
- explanation: string

## 6. Permission Model

Permissions may apply to:

- provider usage
- tool/plugin usage
- network access
- file mutation
- human approval bypass attempts
- route escalation into restricted models or tools

Permissions must be policy-defined, not UI-invented.

## 7. Human Approval Rules

Human approval is mandatory when:

- a blocked category cannot be auto-resolved
- a restricted tool or action requires manual authorization
- confidence is critically low for a high-impact action
- branch / merge selection has material external consequences

## 8. First Implementation Scope

The first implementation should support:

- risk tier classification scaffold
- block / restrict / allow decisions
- tool/plugin permission checks
- reason_code output
- trace logging
- human-review-required signal

## 9. Non-Goals for v0.1

Not required initially:

- universal enterprise policy language
- self-authorizing policy override
- hidden automatic exceptions
- UI-side policy simulation as source of truth

## 10. Final Decision

The Policy / Safety Gate is the official trust boundary of the precision track.

It exists so that Nexa can be:
powerful but stoppable
not:
powerful but structurally careless
