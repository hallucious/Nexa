# Budget-Aware Routing Spec v0.1

## Recommended save path
`docs/specs/precision/budget_aware_routing_spec.md`

## 1. Purpose

This document defines the official Budget-Aware Routing system for Nexa.

Its purpose is to route provider/model/plugin choices using:

- difficulty
- risk
- quality target
- latency target
- budget limit
- retry state

This system prevents expensive execution from becoming default behavior.

## 2. Core Decision

Nexa must not assume that "more expensive" means "better enough to justify cost."

Official rule:

- routing must be policy-driven
- budget must be explicit
- routing must be explainable after execution

## 3. Position in Architecture

Task / Node Context
→ routing estimator
→ route decision
→ execution
→ route log
→ later analysis

## 4. Core Principles

1. budget is explicit
2. routing must be explainable
3. difficulty and risk should influence route choice
4. final route decisions must be logged
5. retries may escalate route quality
6. route choice must be verifier-aware
7. route choice must remain policy-bounded

## 5. Canonical Inputs

RoutingContext
- node_id
- task_type
- difficulty_estimate
- risk_level
- latency_target
- quality_target
- current_budget
- retry_count
- prior_failures
- safety_requirements
- allowed_providers
- allowed_models
- allowed_plugins

## 6. Canonical Outputs

RouteDecision
- route_id: string
- selected_provider_id: string
- selected_model_id: optional string
- selected_plugins: list[string]
- estimated_cost: float
- estimated_latency: float
- selected_route_tier: enum("cheap", "balanced", "high_quality", "high_safety")
- selection_reason_codes: list[string]
- fallback_plan: FallbackPlan
- explanation: string

FallbackPlan
- enabled: bool
- fallback_route_ids: list[string]
- escalation_rules: list[string]

## 7. Difficulty Estimation

Initial difficulty estimation may use:

- input size
- requested output complexity
- required structure strictness
- safety sensitivity
- reasoning depth requirement
- prior verifier failure history

Difficulty estimation must be approximate but explicit.

## 8. Budget Policy

Budget policy may define:

- per-node max cost
- per-run max cost
- per-branch max cost
- per-retry escalation ceiling
- provider/model ban lists
- preferred cheap path for low-risk work

## 9. Route Logging Rules

Every final route must record:

- what was chosen
- what alternatives existed if known
- why this route won
- what budget tier applied
- whether fallback was armed
- whether later verifier results contradicted route adequacy

## 10. First Implementation Scope

The first implementation should support:

- difficulty estimate scaffold
- route tiers
- provider/model choice policy
- cost ceiling
- retry-aware escalation
- route logging
- fallback plan declaration

## 11. Non-Goals for v0.1

Not required initially:

- perfect token-price forecasting
- global optimal routing solver
- unrestricted dynamic market routing
- self-learning router without governance

## 12. Final Decision

Budget-Aware Routing is the official cost-discipline layer for the precision track.

It ensures Nexa becomes:
quality-controlled and cost-aware

instead of:
quality-seeking but financially uncontrolled
