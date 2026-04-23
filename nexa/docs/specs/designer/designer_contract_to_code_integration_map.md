# Designer Contract-to-Code Integration Map v0.1

## Recommended save path
`docs/specs/designer/designer_contract_to_code_integration_map.md`

## 1. Purpose

This document maps the Designer specification bundle to the runtime/storage/UI code areas that must consume it.

Its purpose is to keep implementation work contract-aware and reduce drift between the spec bundle and code layout.

## 2. Mapping Table

| Contract / Spec Role | Primary code sector | Responsibility |
|---|---|---|
| `designer_session_state_card.md` | `src/designer/` session-state assembly | build explicit designer input state |
| `semantic_intent_contract.md` | `src/designer/semantic_*` | bounded semantic interpretation |
| `grounded_intent_contract.md` + `semantic_to_grounding_boundary_spec.md` | `src/designer/grounding_*` | deterministic reference resolution |
| `designer_intent_contract.md` | `src/designer/models/` | normalized intent surface |
| `circuit_patch_contract.md` | `src/designer/patch_*` | explicit mutation planning |
| `designer_validator_precheck_contract.md` | `src/designer/precheck_*` | future-state validation |
| `circuit_draft_preview_contract.md` | `src/designer/preview_*` | user-facing proposal explanation |
| `designer_approval_flow_contract.md` | `src/designer/approval_*` | approval-state handling |
| `approval_to_commit_gateway_rules.md` | storage / commit gateway | approved-truth boundary |
| `designer_governance_contract.md` | UI adapter + designer panel | preserve engine-owned governance |

## 3. Cross-Cutting Sectors

### 3.1 Storage
Designer contracts must preserve:
- Working Save draft semantics
- Commit Snapshot approved-truth semantics

### 3.2 UI
UI sectors such as adapter/designer panel may project Designer truth but must not own:
- preview generation
- precheck status
- commit eligibility

### 3.3 Tests
Tests must cover:
- contract models
- normalization/grounding
- proposal-flow stage transitions
- storage-role boundaries
- UI adapter fidelity

## 4. Decision

Designer contracts must be connected to code as a map of responsibilities, not as an isolated documentation island.
