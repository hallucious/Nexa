# Semantic Intent Contract v0.1

## Recommended save path
`docs/specs/designer/semantic_intent_contract.md`

## 1. Purpose

This document defines the canonical Stage 1 output contract for the next-generation Designer request normalization pipeline.

Its purpose is to make the semantic interpretation layer explicit before implementation.

Stage 1 is the layer that interprets user natural-language design requests with non-deterministic language understanding.
It may use an LLM.
It must not directly commit structural truth.
It must not directly resolve canonical runtime/resource identifiers.

This contract exists to ensure that Designer AI may be flexible in semantic interpretation while remaining bounded by explicit downstream contracts.

## 2. Position in the Designer Pipeline

Canonical next-generation flow:

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

This document defines only the `SemanticIntent` boundary.
It does not define grounding, patch construction, or commit behavior.

## 3. Core Decision

The semantic interpretation layer is allowed to be non-deterministic in language understanding.

Official rule:

- Stage 1 may use an LLM.
- Stage 1 may interpret intent, meaning, likely targets, and likely requested changes.
- Stage 1 must return structured output.
- Stage 1 must not assert canonical IDs as authoritative structural truth.
- Stage 1 must express targets and resources as descriptors, hints, and semantic candidates.

In short:

**Stage 1 produces semantic intent, not grounded structural intent.**

## 4. Non-Goals

Stage 1 must not:

- mutate savefiles directly
- create patch operations directly against committed truth
- resolve final node/provider/plugin/prompt IDs as authoritative outputs
- bypass validation, preview, approval, or commit boundaries
- silently infer approval

## 5. Canonical Output Object

```text
SemanticIntent
- semantic_intent_id: string
- schema_version: string
- source_request_text: string
- session_ref: optional string
- primary_category: SemanticCategory
- requested_outcome: RequestedOutcome
- semantic_actions: list[SemanticAction]
- global_constraints: optional SemanticConstraintSet
- ambiguity_report: AmbiguityReport
- confidence_report: ConfidenceReport
- interpretation_notes: list[string]
- raw_model_notes: optional object
```

## 6. Semantic Category

```text
SemanticCategory
- CREATE_CIRCUIT
- MODIFY_CIRCUIT
- EXPLAIN_CIRCUIT
- ANALYZE_CIRCUIT
- REPAIR_CIRCUIT
- OPTIMIZE_CIRCUIT
```

Rules:

- exactly one primary category is required
- category is semantic, not yet structurally grounded
- downstream layers may reject or escalate an implausible category, but Stage 1 must still choose one

## 7. Requested Outcome

```text
RequestedOutcome
- summary: string
- success_shape: optional string
- bounded_scope_hint: optional string
- human_intent_notes: optional list[string]
```

Purpose:

- capture what the user appears to want overall
- preserve high-level semantic intent even if later grounding fails

## 8. Semantic Action

A `SemanticIntent` may contain one or more semantic actions.

```text
SemanticAction
- action_id: string
- action_type: SemanticActionType
- target_descriptor: optional TargetDescriptor
- resource_descriptor: optional ResourceDescriptor
- placement_descriptor: optional PlacementDescriptor
- parameter_descriptors: optional list[ParameterDescriptor]
- rationale: optional string
- confidence: low | medium | high
- ambiguity_flags: optional list[SemanticAmbiguityFlag]
```

Rules:

- actions are semantic requests, not patch operations
- actions may be incomplete if the request is ambiguous
- actions must remain reviewable and groundable
- actions may not contain hidden executable mutation instructions

## 9. Semantic Action Type

```text
SemanticActionType
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

Rules:

- this action vocabulary is semantic and may be broader than the immediate patch vocabulary
- unsupported action types must be rejected before patch build

## 10. Target Descriptor

Stage 1 must describe likely targets without asserting canonical IDs.

```text
TargetDescriptor
- entity_kind: node | edge | output | circuit | subgraph | unknown
- label_hint: optional string
- role_hint: optional string
- position_hint: optional string
- ordinal_hint: optional string
- relationship_hint: optional string
- explicit_user_reference: optional string
- candidate_reference_text: optional string
```

Examples:

- `label_hint = "reviewer"`
- `role_hint = "review"`
- `position_hint = "middle"`
- `ordinal_hint = "second"`
- `relationship_hint = "final step before judge"`

Rules:

- `TargetDescriptor` is descriptive, not authoritative
- it must not be treated as a canonical engine reference
- it may preserve the user's own wording for downstream grounding

## 11. Resource Descriptor

Stage 1 must describe requested resources semantically.

```text
ResourceDescriptor
- resource_kind: provider | plugin | prompt | parameter | unknown
- family_hint: optional string
- capability_hint: optional string
- label_hint: optional string
- style_hint: optional string
- user_reference_text: optional string
```

Examples:

- provider: `family_hint = "claude"`
- plugin: `capability_hint = "search tool"`
- prompt: `label_hint = "strict review prompt"`

Rules:

- Stage 1 may state semantic family/capability/label hints
- Stage 1 must not invent final canonical resource IDs as authoritative outputs

## 12. Placement Descriptor

```text
PlacementDescriptor
- placement_kind: before | after | between | replace | inside | around | unknown
- anchor_a_hint: optional string
- anchor_b_hint: optional string
- relationship_text: optional string
```

Examples:

- `before final judge`
- `between the reviewer and the final judge`
- `replace the middle node`

Rules:

- placement remains semantic until grounded against actual topology

## 13. Parameter Descriptor

```text
ParameterDescriptor
- name_hint: string
- value_hint: optional string
- semantic_type: optional string
- user_reference_text: optional string
```

Purpose:

- capture requested parameter meaning without assuming exact downstream schema paths

## 14. Semantic Constraint Set

```text
SemanticConstraintSet
- preserve_existing_structure: optional bool
- minimize_change_scope: optional bool
- prefer_existing_resources: optional bool
- human_review_required: optional bool
- cost_sensitivity: optional low | medium | high
- speed_sensitivity: optional low | medium | high
- quality_priority: optional low | medium | high
```

Rules:

- Stage 1 may infer broad design constraints from user language
- downstream validation remains authoritative

## 15. Ambiguity Report

```text
AmbiguityReport
- overall_ambiguity: low | medium | high
- unresolved_items: list[SemanticAmbiguityItem]
```

```text
SemanticAmbiguityItem
- ambiguity_type: target | resource | placement | scope | category | parameter | other
- description: string
- severity: low | medium | high
- clarification_would_help: bool
```

Rules:

- ambiguity must be explicit, not hidden in free text
- Stage 1 is allowed to continue with partial semantic actions if ambiguity is surfaced

## 16. Confidence Report

```text
ConfidenceReport
- overall_confidence: low | medium | high
- reasons: list[string]
```

Rules:

- confidence is advisory only
- low confidence does not block the pipeline by itself
- downstream systems may use confidence for clarification or stricter review

## 17. Canonical Prohibitions

Stage 1 outputs are invalid if they:

1. treat guessed canonical IDs as authoritative truth
2. contain direct patch operations against committed structure
3. suppress ambiguity that materially affects structure
4. imply approval or commit
5. bypass the Designer proposal boundary

## 18. Example

```json
{
  "semantic_intent_id": "sem_001",
  "schema_version": "0.1",
  "source_request_text": "Have the reviewer use Claude instead.",
  "primary_category": "MODIFY_CIRCUIT",
  "requested_outcome": {
    "summary": "Change the provider used by the review step."
  },
  "semantic_actions": [
    {
      "action_id": "act_001",
      "action_type": "replace_provider",
      "target_descriptor": {
        "entity_kind": "node",
        "label_hint": "reviewer",
        "role_hint": "review"
      },
      "resource_descriptor": {
        "resource_kind": "provider",
        "family_hint": "claude"
      },
      "confidence": "high"
    }
  ],
  "ambiguity_report": {
    "overall_ambiguity": "low",
    "unresolved_items": []
  },
  "confidence_report": {
    "overall_confidence": "high",
    "reasons": [
      "Clear modify intent and clear provider family hint."
    ]
  },
  "interpretation_notes": []
}
```

## 19. Relationship to Existing Designer Contracts

This contract does not replace:

- `designer_intent_contract.md`
- `circuit_patch_contract.md`
- `designer_validator_precheck_contract.md`
- `designer_session_state_card.md`

Instead:

- `SemanticIntent` is the new Stage 1 interpretation boundary
- a later grounded stage must convert semantic intent into a structurally usable form
- existing downstream proposal contracts remain in force

## 20. Migration Direction

Recommended migration order:

1. fix this contract
2. implement `semantic_interpreter.py`
3. implement `symbolic_grounder.py`
4. convert `request_normalizer.py` into a compatibility facade
5. stabilize tests
6. reduce/remove facade behavior later
