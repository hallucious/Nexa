# Designer Spec Index v0.2

## Recommended save path
`docs/specs/designer/designer_spec_index.md`

## 1. Purpose

This document is the official index for the Designer specification bundle in Nexa.

Its purpose is to:

- define the canonical document set for the Designer layer
- explain the role of each document
- fix the recommended reading order
- clarify which document is authoritative for which question
- reduce future ambiguity during implementation and review

## 2. Why This Index Exists

Designer AI is not a one-file feature.

It affects multiple specification layers at once:

- session-state exposure
- intent normalization
- semantic interpretation
- symbolic grounding
- patch planning
- precheck evaluation
- preview generation
- approval and commit boundaries

Without an index, future implementation work may drift because different documents answer different kinds of questions.

This index exists to prevent that drift.

## 3. Canonical Designer Spec Bundle

### 3.1 Input / Session Boundary
- `designer_session_state_card.md`
- `designer_ai_input_exposure_rules.md`
- `designer_ai_input_priority_rules.md`
- `designer_ai_input_redaction_rules.md`
- `designer_ai_input_refresh_triggers.md`

### 3.2 Interpretation and Grounding Boundary
- `semantic_intent_contract.md`
- `grounded_intent_contract.md`
- `semantic_to_grounding_boundary_spec.md`
- `designer_intent_contract.md`
- `session_card_to_intent_mapping_rules.md`

### 3.3 Proposal Construction Boundary
- `circuit_patch_contract.md`
- `intent_to_patch_mapping_rules.md`
- `patch_plan_to_precheck_evaluation_rules.md`

### 3.4 Review / Approval Boundary
- `designer_validator_precheck_contract.md`
- `circuit_draft_preview_contract.md`
- `precheck_to_preview_mapping_rules_recreated.md`
- `preview_to_approval_decision_rules_recreated.md`
- `designer_approval_flow_contract.md`
- `approval_to_commit_gateway_rules_recreated.md`

### 3.5 Placement / Audit Documents
- `designer_document_placement_and_gap_audit.md`

## 4. Recommended Reading Order

1. `designer_session_state_card.md`
2. `semantic_intent_contract.md`
3. `grounded_intent_contract.md`
4. `semantic_to_grounding_boundary_spec.md`
5. `designer_intent_contract.md`
6. `circuit_patch_contract.md`
7. `designer_validator_precheck_contract.md`
8. `circuit_draft_preview_contract.md`
9. `designer_approval_flow_contract.md`

## 5. Authority by Question

### 5.1 What does Designer AI receive as input?
Authoritative document:
- `designer_session_state_card.md`

### 5.2 What may the LLM-based interpretation layer output?
Authoritative document:
- `semantic_intent_contract.md`

### 5.3 How is semantic meaning resolved into actual structural references?
Authoritative documents:
- `grounded_intent_contract.md`
- `semantic_to_grounding_boundary_spec.md`

### 5.4 What is the broader normalized Designer intent shape?
Authoritative document:
- `designer_intent_contract.md`

### 5.5 How are grounded design requests translated into patch proposals?
Authoritative documents:
- `circuit_patch_contract.md`
- `intent_to_patch_mapping_rules.md`

### 5.6 What happens before commit?
Authoritative documents:
- `designer_validator_precheck_contract.md`
- `circuit_draft_preview_contract.md`
- `designer_approval_flow_contract.md`

## 6. Current Architectural Direction

The current Designer direction is:

- non-deterministic semantic interpretation is allowed in the Designer layer
- symbolic grounding must remain deterministic
- patch / precheck / preview / approval / commit boundaries remain explicit
- migration should proceed through a compatibility facade rather than a one-step deletion of the legacy normalizer

## 7. Implementation Direction

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

## 8. Decision

The Designer specification bundle now includes an explicit Stage 1 / Stage 2 split.

That split is defined by:

- `semantic_intent_contract.md`
- `grounded_intent_contract.md`
- `semantic_to_grounding_boundary_spec.md`

These documents must be fixed before the next implementation step.
