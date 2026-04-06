# Grounded Intent Contract v0.1

## Recommended save path
`docs/specs/designer/grounded_intent_contract.md`

## 1. Purpose

This document defines the canonical Stage 2 output contract for the next-generation Designer normalization pipeline.

Its purpose is to convert semantic interpretation into a structurally usable, deterministically grounded design intent without crossing the patch/approval boundary.

Stage 2 is the symbolic grounding layer.
It must be deterministic relative to:

- the `SemanticIntent`
- the current Designer Session State Card
- the current Working Save / available resources / topology

## 2. Position in the Designer Pipeline

Canonical flow:

```text
User Request
-> Designer Session State Card
-> Semantic Interpreter
-> SemanticIntent
-> Symbolic Grounder
-> GroundedIntent
-> Patch Builder
-> Validator Precheck
-> Draft Preview
-> Approval
-> Commit
```

This document defines only the `GroundedIntent` boundary.
It does not define LLM prompting or patch application.

## 3. Core Decision

Stage 2 is responsible for canonical grounding.

Official rule:

- Stage 2 resolves semantic descriptors against current structural reality.
- Stage 2 determines canonical node/resource/topology references.
- Stage 2 is deterministic.
- Stage 2 may reject or partially ground semantic actions.
- Stage 2 must not fabricate nonexistent canonical IDs.

In short:

**Stage 2 produces grounded structural intent, but not patch operations or committed mutation.**

## 4. Non-Goals

Stage 2 must not:

- perform patch application
- bypass precheck, preview, approval, or commit
- silently invent node/resource IDs not present in the current grounded universe
- re-run open-ended natural-language interpretation as if it were Stage 1

## 5. Canonical Output Object

```text
GroundedIntent
- grounded_intent_id: string
- schema_version: string
- semantic_intent_ref: string
- session_ref: optional string
- primary_category: GroundedCategory
- grounded_actions: list[GroundedAction]
- preserved_constraints: optional GroundedConstraintSet
- grounding_report: GroundingReport
- unresolved_actions: list[UnresolvedGroundingItem]
- escalation_flags: list[GroundingEscalationFlag]
- explanation: optional string
```

## 6. Grounded Category

`GroundedCategory` uses the same category vocabulary as the Designer intent layer, but the category is now bound to current structural reality.

```text
GroundedCategory
- CREATE_CIRCUIT
- MODIFY_CIRCUIT
- EXPLAIN_CIRCUIT
- ANALYZE_CIRCUIT
- REPAIR_CIRCUIT
- OPTIMIZE_CIRCUIT
```

Rules:

- category should normally match the semantic stage
- a downstream rejection/escalation may occur if semantic category conflicts with actual grounded scope

## 7. Grounded Action

```text
GroundedAction
- action_id: string
- source_semantic_action_ref: string
- action_type: GroundedActionType
- target_binding: optional TargetBinding
- resource_binding: optional ResourceBinding
- placement_binding: optional PlacementBinding
- grounded_parameters: optional list[GroundedParameter]
- grounding_status: grounded | partially_grounded | unresolved | rejected
- rationale: optional string
- grounding_notes: optional list[string]
```

Rules:

- every grounded action must retain traceability back to the semantic action
- grounded actions are still not patch operations
- unresolved or rejected actions must remain explicit

## 8. Grounded Action Type

```text
GroundedActionType
- create_node
- delete_node
- update_node
- replace_provider
- attach_plugin
- detach_plugin
- replace_prompt
- insert_node
- connect_nodes
- disconnect_nodes
- move_output
- define_output
- rename_component
- explain_structure
- analyze_risk
- analyze_cost
- repair_structure
- optimize_structure
```

## 9. Target Binding

```text
TargetBinding
- entity_kind: node | edge | output | circuit | subgraph
- canonical_ref: string
- display_label: optional string
- matched_from: optional string
- match_confidence: low | medium | high
```

Examples:

- `canonical_ref = "node.reviewer"`
- `canonical_ref = "edge.reviewer__final_judge"`
- `canonical_ref = "output.final_result"`

Rules:

- `canonical_ref` must exist in the current grounding universe
- nonexistent canonical refs are invalid
- if no satisfactory target exists, the action must remain unresolved rather than fabricated

## 10. Resource Binding

```text
ResourceBinding
- resource_kind: provider | plugin | prompt | parameter
- canonical_id: string
- matched_family: optional string
- matched_capability: optional string
- match_confidence: low | medium | high
```

Examples:

- `canonical_id = "anthropic:claude-sonnet"`
- `canonical_id = "web.search"`
- `canonical_id = "strict_review_prompt"`

Rules:

- canonical IDs must come from the available grounding universe
- grounding must prefer actual allowed/available resources over guessed IDs
- if multiple candidates remain, the ambiguity must remain visible

## 11. Placement Binding

```text
PlacementBinding
- placement_kind: before | after | between | replace | inside
- anchor_a_ref: optional string
- anchor_b_ref: optional string
- derived_topology_notes: optional list[string]
- match_confidence: low | medium | high
```

Rules:

- placement must be resolved against actual node/edge topology
- `between` must include both anchors when grounded
- impossible placement requests must remain unresolved or rejected

## 12. Grounded Parameter

```text
GroundedParameter
- name: string
- value: string | number | bool | object | list | null
- source: semantic_hint | topology_derivation | resource_match | default_inference
- confidence: low | medium | high
```

Rules:

- every grounded parameter should preserve its provenance where possible
- hidden parameter fabrication is forbidden for structurally meaningful values

## 13. Grounded Constraint Set

```text
GroundedConstraintSet
- preserve_existing_structure: optional bool
- minimize_change_scope: optional bool
- prefer_existing_resources: optional bool
- human_review_required: optional bool
- cost_sensitivity: optional low | medium | high
- speed_sensitivity: optional low | medium | high
- quality_priority: optional low | medium | high
```

Purpose:

- carry forward semantic constraints in a structurally usable form

## 14. Grounding Report

```text
GroundingReport
- overall_status: grounded | partially_grounded | unresolved | rejected
- resolved_target_count: int
- resolved_resource_count: int
- unresolved_count: int
- rejected_count: int
- findings: list[GroundingFinding]
```

```text
GroundingFinding
- finding_type: target_match | resource_match | placement_match | ambiguity | rejection | incompatibility | scope_violation
- severity: low | medium | high
- description: string
- related_action_id: optional string
```

## 15. Unresolved Grounding Item

```text
UnresolvedGroundingItem
- action_ref: string
- unresolved_type: target | resource | placement | parameter | scope | category | other
- description: string
- clarification_needed: bool
```

Purpose:

- preserve precisely what could not be grounded
- avoid silent fallback to invented structure

## 16. Grounding Escalation Flag

```text
GroundingEscalationFlag
- flag_type: clarification_required | candidate_conflict | scope_conflict | missing_resource | missing_target | topology_conflict
- severity: low | medium | high
- description: string
```

Purpose:

- allow downstream systems to trigger clarification, stricter review, or precheck handling

## 17. Canonical Prohibitions

Grounded output is invalid if it:

1. invents canonical refs not present in the current universe
2. suppresses unresolved grounding problems that materially affect structure
3. applies patch operations directly
4. implies approval or commit
5. silently changes the current grounding universe

## 18. Example

```json
{
  "grounded_intent_id": "gnd_001",
  "schema_version": "0.1",
  "semantic_intent_ref": "sem_001",
  "primary_category": "MODIFY_CIRCUIT",
  "grounded_actions": [
    {
      "action_id": "act_001",
      "source_semantic_action_ref": "act_001",
      "action_type": "replace_provider",
      "target_binding": {
        "entity_kind": "node",
        "canonical_ref": "node.reviewer",
        "display_label": "Reviewer",
        "matched_from": "reviewer",
        "match_confidence": "high"
      },
      "resource_binding": {
        "resource_kind": "provider",
        "canonical_id": "anthropic:claude-sonnet",
        "matched_family": "claude",
        "match_confidence": "high"
      },
      "grounding_status": "grounded"
    }
  ],
  "grounding_report": {
    "overall_status": "grounded",
    "resolved_target_count": 1,
    "resolved_resource_count": 1,
    "unresolved_count": 0,
    "rejected_count": 0,
    "findings": []
  },
  "unresolved_actions": [],
  "escalation_flags": []
}
```

## 19. Relationship to Existing Designer Contracts

`GroundedIntent` is the bridge between:

- Stage 1 semantic interpretation
- existing patch/precheck/preview/approval flow

This contract does not replace:

- `designer_intent_contract.md`
- `circuit_patch_contract.md`
- `designer_validator_precheck_contract.md`

Instead:

- `GroundedIntent` is the structurally usable input to later patch planning
- downstream patch building may remain deterministic and schema-bounded

## 20. Migration Direction

Recommended migration order:

1. fix this contract alongside `semantic_intent_contract.md`
2. implement `symbolic_grounder.py`
3. adapt patch builder / proposal flow to consume grounded intent
4. convert `request_normalizer.py` into a compatibility facade
5. stabilize tests before removing facade logic
