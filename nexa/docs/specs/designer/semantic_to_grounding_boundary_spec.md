# Semantic to Grounding Boundary Spec v0.1

## Recommended save path
`docs/specs/designer/semantic_to_grounding_boundary_spec.md`

## 1. Purpose

This document defines the canonical boundary between Stage 1 semantic interpretation and Stage 2 symbolic grounding in the next-generation Designer pipeline.

Its purpose is to prevent semantic interpretation and structural grounding from drifting back into one mixed implementation.

This specification exists because the project has decided to:

- allow non-deterministic semantic interpretation in the Designer layer
- keep structural grounding deterministic
- preserve the existing proposal / precheck / approval / commit boundary

## 2. Pipeline Position

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

This document defines only the Stage 1 -> Stage 2 handoff.

## 3. Core Decision

Stage 1 and Stage 2 must be separate subsystems with separate responsibilities.

Official rule:

- Stage 1 interprets meaning.
- Stage 2 resolves meaning against actual structural reality.
- Stage 1 is allowed to be non-deterministic.
- Stage 2 must be deterministic.
- Stage 1 must not output authoritative canonical IDs.
- Stage 2 must not behave like a second open-ended natural-language interpreter.

In short:

**Stage 1 describes what the user seems to mean.
Stage 2 decides what that meaning can validly bind to in the current design state.**

## 4. Stage 1 Responsibility

Stage 1 owns:

- semantic category inference
- high-level requested outcome interpretation
- semantic action extraction
- target/resource/placement/parameter descriptors
- ambiguity surfacing
- confidence surfacing

Stage 1 does not own:

- canonical node IDs
- canonical provider/plugin/prompt IDs
- topology-verified placement binding
- final structural target resolution
- patch operation construction

## 5. Stage 2 Responsibility

Stage 2 owns:

- canonical target resolution
- canonical resource resolution
- topology-aware placement resolution
- explicit unresolved/rejected grounding outcomes
- conflict and escalation surfacing
- preparation of structurally usable grounded intent

Stage 2 does not own:

- open-ended natural-language reinterpretation
- LLM prompting for broad request meaning
- approval, preview, or commit
- patch application

## 6. Canonical Handoff Principle

The handoff between Stage 1 and Stage 2 must be:

1. structured
2. reviewable
3. traceable
4. non-authoritative with respect to canonical IDs
5. deterministic to consume

This means Stage 1 must emit descriptors and hints, not final structural truth.

## 7. Canonical Handoff Rules

### 7.1 Stage 1 Output Shape Rule

Stage 1 must produce `SemanticIntent` only.

It must not skip directly to:

- `GroundedIntent`
- patch operations
- commit-ready state

### 7.2 Canonical ID Rule

Stage 1 may preserve user text such as:

- `reviewer`
- `Claude`
- `strict review prompt`
- `before the final judge`

But Stage 1 must not treat guessed forms such as:

- `node.reviewer`
- `anthropic:claude-sonnet`
- `prompt.strict_review`

as authoritative structural truth.

### 7.3 Grounding Universe Rule

Stage 2 must ground only against the current allowed grounding universe.

The grounding universe is derived from current Designer context, including:

- current Working Save
- node list
- edge list
- outputs
- available prompt refs
- available provider refs
- available plugin refs
- current selection / target scope context

### 7.4 No Fabrication Rule

If Stage 2 cannot resolve a canonical target/resource/placement from the actual grounding universe, it must:

- mark the action unresolved
- or reject the action
- or raise clarification/escalation

It must not fabricate a plausible-looking canonical ID.

### 7.5 No Semantic Re-Parse Rule

Stage 2 may use deterministic matching, ranking, and topology derivation.
It must not silently perform another open-ended semantic interpretation pass.

### 7.6 Provenance Rule

Every grounded result should preserve traceability to:

- source semantic action
- source descriptor fields
- matching basis
- confidence / ambiguity findings

## 8. Handoff Data Requirements

At minimum, Stage 1 must provide enough descriptor information for Stage 2 to attempt deterministic grounding.

Required minimum semantic payload per action:

```text
- action_type
- target_descriptor or explicit no-target state
- optional resource_descriptor
- optional placement_descriptor
- action-level ambiguity flags
```

Stage 2 must not be forced to parse unconstrained free text alone.

## 9. Allowed vs Forbidden Boundary Shapes

### Allowed

```json
{
  "action_type": "replace_provider",
  "target_descriptor": {
    "entity_kind": "node",
    "label_hint": "reviewer",
    "role_hint": "review"
  },
  "resource_descriptor": {
    "resource_kind": "provider",
    "family_hint": "claude"
  }
}
```

### Forbidden

```json
{
  "action_type": "replace_provider",
  "target_node": "node.reviewer",
  "provider_id": "anthropic:claude-sonnet-3.7"
}
```

Reason:

- the JSON shape may be valid syntactically
- but it collapses semantic interpretation and canonical grounding into one unsafe step

## 10. Grounding Outcomes

Stage 2 may produce four broad outcomes per action:

```text
grounded
partially_grounded
unresolved
rejected
```

These outcomes must remain explicit for downstream patch/precheck logic.

## 11. Clarification and Escalation Boundary

If Stage 2 cannot safely resolve meaning into structure, it may emit:

- clarification-required flags
- candidate-conflict flags
- missing-resource flags
- topology-conflict flags

The boundary must not silently choose a structurally meaningful action when ambiguity remains material.

## 12. Observability Requirement

The Stage 1 -> Stage 2 handoff must be observable in logs/trace/debug output.

Minimum observable artifacts:

- raw semantic intent
- grounded intent result
- grounding findings
- unresolved/rejected items

Purpose:

- support debugging
- separate semantic failures from grounding failures
- keep future evaluation measurable

## 13. Implementation Direction

Recommended implementation split:

```text
src/designer/
├── semantic_interpreter.py
├── symbolic_grounder.py
├── proposal_flow.py
└── request_normalizer.py   # compatibility facade during migration
```

Recommended model split:

```text
src/designer/models/
├── semantic_intent.py
└── grounded_intent.py
```

## 14. Migration Rule

Recommended migration sequence:

1. fix `semantic_intent_contract.md`
2. fix `grounded_intent_contract.md`
3. fix this boundary spec
4. implement `semantic_interpreter.py`
5. implement `symbolic_grounder.py`
6. route existing `request_normalizer.py` through the new layers as a compatibility facade
7. stabilize tests
8. shrink/remove facade later

## 15. Relationship to Existing Designer Architecture

This boundary specification does not alter the downstream proposal boundary.

The following remain in force:

- patch planning remains explicit
- precheck remains mandatory
- preview remains mandatory for structural proposals
- approval remains explicit
- commit remains gated

This specification changes only the internal interpretation architecture used before patch construction.
