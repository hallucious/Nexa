# Designer Intent Contract v0.1

## 1. Purpose

This contract defines the normalized intent schema between:
- user natural-language design request
- Designer AI interpretation layer
- circuit draft / patch builder
- validation layer

Designer AI must output **structured design intent**, not hidden savefile mutation.

## 2. Core Principles

1. Designer AI outputs explicit normalized intent.
2. Intent must be previewable before commit.
3. Ambiguous or destructive requests must become safe proposals.
4. Validation runs after intent generation and before commit.
5. Designer AI may propose, but may not silently redefine engine/runtime contracts.

## 3. Primary Intent Categories

- `CREATE_CIRCUIT`
- `MODIFY_CIRCUIT`
- `EXPLAIN_CIRCUIT`
- `ANALYZE_CIRCUIT`
- `REPAIR_CIRCUIT`
- `OPTIMIZE_CIRCUIT`

Exactly one primary category must be chosen.

## 4. Normalized Intent Schema

```text
NormalizedIntent
- intent_id
- category
- user_request_text
- target_scope
- objective
- constraints
- proposed_actions
- assumptions
- ambiguity_flags
- risk_flags
- requires_user_confirmation
- confidence
- explanation
```

## 5. Target Scope

```text
TargetScope
- mode: new_circuit | existing_circuit | subgraph_only | node_only | read_only
- savefile_ref
- node_refs
- edge_refs
- max_change_scope: minimal | bounded | broad
```

Rules:
- create -> `new_circuit`
- explain/analyze -> `read_only`
- modify/repair/optimize must explicitly declare touched scope

## 6. Objective Specification

```text
ObjectiveSpec
- primary_goal
- secondary_goals
- success_criteria
- preferred_behavior
```

## 7. Constraint Set

```text
ConstraintSet
- cost_limit
- speed_priority
- quality_priority
- determinism_preference
- provider_preferences
- provider_restrictions
- plugin_preferences
- plugin_restrictions
- human_review_required
- safety_level
- output_requirements
- forbidden_patterns
```

## 8. Action Specification

Designer AI must emit explicit actions.

```text
ActionSpec
- action_type
- target_ref
- parameters
- rationale
```

Supported action types include:
- create_node
- delete_node
- update_node
- connect_nodes
- disconnect_nodes
- insert_node_between
- replace_provider
- attach_plugin
- detach_plugin
- set_prompt
- set_parameter
- add_review_gate
- remove_review_gate
- define_output
- rename_component

## 9. Assumptions

```text
AssumptionSpec
- text
- severity: low | medium | high
- user_visible
```

Hidden structural assumptions are forbidden.

## 10. Ambiguity Flags

```text
AmbiguityFlag
- type
- description
```

If ambiguity changes circuit shape materially, confirmation is required.

## 11. Risk Flags

```text
RiskFlag
- type
- severity
- description
```

High-severity risks must block silent auto-commit.

## 12. Decision

Designer AI is a proposal-producing design layer.
It must output normalized intent first.
No hidden direct savefile mutation is allowed.

## 13. Designer Constraint Integration (v0.2)
Designer intent normalization now operates under an explicit constraint system.
That constraint layer MUST keep Designer behavior:

- bounded
- lintable
- critiqueable
- simulation-checkable before commit

At minimum the constraint system may define:
- allowed node kinds / resource types
- forbidden structural patterns
- mandatory verifier requirements on risky paths
- complexity / depth ceilings
- pre-review auto-critique findings

Designer remains proposal-producing. The constraint system tightens proposal quality; it does not grant hidden authority.

