# Designer Spec Index v0.1

## Recommended save path
`docs/specs/designer/designer_spec_index.md`

## 1. Purpose

This document is the official index for the Designer-related specification bundle in Nexa.

Its purpose is to:

- define the canonical document set for Designer AI
- separate input-boundary specs from downstream proposal-pipeline specs
- clarify which documents are needed now vs later
- fix the recommended reading order
- reduce future drift during implementation and review

This index does not replace the detailed specs.
It organizes them.

## 2. Why This Index Exists

Designer AI is not a single document feature.

It spans multiple layers:

- design-layer architecture
- input exposure boundary
- intent generation boundary
- patch generation boundary
- proposal evaluation boundary
- preview / approval / commit boundary

Without an index, the project can easily confuse:

- what Designer AI is allowed to see
with
- what Designer AI does after seeing it

This index exists to prevent that confusion.

## 3. Canonical Designer Spec Bundle

The canonical v0.1 bundle is divided into two groups:

1. input-boundary specs
2. downstream pipeline specs

---

## 4. Group A — Input-Boundary Specs

These are the documents that define what information is given to Designer AI and under what rules.

### 4.1 Designer AI Integration Architecture
Path:

    docs/specs/architecture/designer_ai_integration_architecture.md

Role:
- defines what Designer AI is in Nexa
- fixes its position above the execution engine
- establishes the proposal-first boundary
- prevents Designer AI from being treated as an execution resource

### 4.2 Designer Session State Card
Path:

    docs/specs/designer/designer_session_state_card.md

Role:
- defines the canonical input card for Designer AI
- fixes the minimum design-state fields Designer AI must receive
- defines the top-level bounded input structure

### 4.3 Designer AI Input Exposure Rules
Path:

    docs/specs/designer/designer_ai_input_exposure_rules.md

Role:
- defines which information may be exposed to Designer AI
- defines summary-first vs scoped exposure rules
- defines always-expose vs conditionally-exposed categories

### 4.4 Designer AI Input Redaction Rules
Path:

    docs/specs/designer/designer_ai_input_redaction_rules.md

Role:
- defines what must be hidden, masked, or downgraded before exposure
- protects secrets, hidden authority, and irrelevant internal noise

### 4.5 Designer AI Input Priority Rules
Path:

    docs/specs/designer/designer_ai_input_priority_rules.md

Role:
- defines conflict resolution precedence
- fixes what wins when scope, constraints, history, and user corrections disagree

### 4.6 Designer AI Input Refresh Triggers
Path:

    docs/specs/designer/designer_ai_input_refresh_triggers.md

Role:
- defines when Designer AI input must be recomputed
- prevents stale design-state projection reuse

---

## 5. Group B — Downstream Proposal Pipeline Specs

These are the documents that define what happens after the input boundary is already fixed.

### 5.1 Designer Intent Contract
Path:

    docs/specs/designer/designer_intent_contract.md

Role:
- defines the normalized intent object
- fixes category, objective, scope, assumptions, ambiguity, and risk structure

### 5.2 Session Card to Intent Mapping Rules
Path:

    docs/specs/designer/session_card_to_intent_mapping_rules.md

Role:
- defines how `DesignerSessionStateCard` becomes `NormalizedIntent`
- fixes category-resolution and scope-preservation rules

### 5.3 Circuit Patch Contract
Path:

    docs/specs/designer/circuit_patch_contract.md

Role:
- defines the canonical patch object
- fixes explicit operation-based circuit mutation proposal structure

### 5.4 Intent to Patch Mapping Rules
Path:

    docs/specs/designer/intent_to_patch_mapping_rules.md

Role:
- defines how `NormalizedIntent` becomes `CircuitPatchPlan`
- fixes operation derivation and patch boundedness rules

### 5.5 Designer Validator Precheck Contract
Path:

    docs/specs/designer/designer_validator_precheck_contract.md

Role:
- defines the structured precommit evaluation object
- fixes blocking / warning / confirmation distinction

### 5.6 Patch Plan to Precheck Evaluation Rules
Path:

    docs/specs/designer/patch_plan_to_precheck_evaluation_rules.md

Role:
- defines how `CircuitPatchPlan` becomes `ValidationPrecheck`
- fixes future-state-aware evaluation rules

### 5.7 Circuit Draft Preview Contract
Path:

    docs/specs/designer/circuit_draft_preview_contract.md

Role:
- defines the canonical preview object
- fixes what users must see before approval

### 5.8 Precheck to Preview Mapping Rules
Path:

    docs/specs/designer/precheck_to_preview_mapping_rules.md

Role:
- defines how `ValidationPrecheck` becomes `CircuitDraftPreview`
- fixes status-faithful preview composition

### 5.9 Preview to Approval Decision Rules
Path:

    docs/specs/designer/preview_to_approval_decision_rules.md

Role:
- defines valid user decision outcomes after preview
- fixes explicit approval semantics

### 5.10 Approval to Commit Gateway Rules
Path:

    docs/specs/designer/approval_to_commit_gateway_rules.md

Role:
- defines when an approved proposal may cross into committed structural truth
- fixes commit eligibility and rejection rules

---

## 6. Recommended Reading Order

### 6.1 For current input-boundary work
Read in this order:

1. `designer_ai_integration_architecture.md`
2. `designer_session_state_card.md`
3. `designer_ai_input_exposure_rules.md`
4. `designer_ai_input_redaction_rules.md`
5. `designer_ai_input_priority_rules.md`
6. `designer_ai_input_refresh_triggers.md`

This is the correct reading path for the question:

    "What information should be provided to the called AI for circuit generation?"

### 6.2 For later full proposal-pipeline work
Read in this order:

1. `designer_intent_contract.md`
2. `session_card_to_intent_mapping_rules.md`
3. `circuit_patch_contract.md`
4. `intent_to_patch_mapping_rules.md`
5. `designer_validator_precheck_contract.md`
6. `patch_plan_to_precheck_evaluation_rules.md`
7. `circuit_draft_preview_contract.md`
8. `precheck_to_preview_mapping_rules.md`
9. `preview_to_approval_decision_rules.md`
10. `approval_to_commit_gateway_rules.md`

---

## 7. What Is Needed Now vs Later

### 7.1 Needed now
These are directly needed for the current work topic:

- Designer AI Integration Architecture
- Designer Session State Card
- Designer AI Input Exposure Rules
- Designer AI Input Redaction Rules
- Designer AI Input Priority Rules
- Designer AI Input Refresh Triggers

### 7.2 Needed later
These are not wrong or obsolete.
They belong to the next implementation track:

- Designer Intent Contract
- Session Card to Intent Mapping Rules
- Circuit Patch Contract
- Intent to Patch Mapping Rules
- Designer Validator Precheck Contract
- Patch Plan to Precheck Evaluation Rules
- Circuit Draft Preview Contract
- Precheck to Preview Mapping Rules
- Preview to Approval Decision Rules
- Approval to Commit Gateway Rules

---

## 8. Canonical Boundary Reminder

The most important distinction in this bundle is:

### Input-boundary question
"What does Designer AI get to see?"

This is answered by:

- Session State Card
- Exposure Rules
- Redaction Rules
- Priority Rules
- Refresh Triggers

### Pipeline question
"What happens after Designer AI has already received the input?"

This is answered by:

- Intent
- Patch
- Precheck
- Preview
- Approval
- Commit

These two categories must not be confused.

---

## 9. Non-Goals of This Index

This index does not:

- replace detailed contracts
- define implementation code
- decide UI rendering details
- redefine storage truth
- grant Designer AI any authority by itself

It only organizes the document system.

---

## 10. Decision

The canonical Designer specification bundle in Nexa has two tracks:

1. input-boundary specs
2. downstream proposal-pipeline specs

The current question belongs to track 1.

This index exists to keep the two tracks separate, ordered, and implementation-safe.
