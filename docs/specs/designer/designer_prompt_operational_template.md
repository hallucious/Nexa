# Designer Prompt Operational Template v0.1

## Recommended save path
`docs/specs/designer/designer_prompt_operational_template.md`

## 1. Purpose

This document defines the practical runtime prompt envelope used when an LLM-backed Designer interpreter is invoked.

Its purpose is to explain how the formal Designer contracts are serialized into operational model input without collapsing the contract boundaries.

## 2. Core Rule

The runtime prompt is an operational projection of the Designer contracts.
It is not allowed to redefine those contracts.

## 3. Input Envelope

The operational prompt should be assembled from these sections:
1. system framing
2. session-state card projection
3. task objective and constraints
4. allowed output contract
5. forbidden behaviors

## 4. Required Input Sections

### 4.1 System framing
Must state that the model is acting as a proposal-producing Designer layer, not as an execution engine and not as a direct savefile mutator.

### 4.2 Session-state projection
Must include the active `DesignerSessionStateCard` or a faithful serialization of:
- storage role
- current working-save state
- selected scope
- available resources
- findings and risks
- revision / approval state

### 4.3 Objective and constraints
Must include:
- user request
- explicit scope bounds
- safety or policy limits
- cost/complexity hints when relevant

### 4.4 Output contract
The model must output only one of the allowed artifacts for the current stage, such as:
- semantic intent
- grounded intent
- patch plan
- preview explanation draft

### 4.5 Forbidden behaviors
Must explicitly forbid:
- direct mutation of committed truth
- hidden assumption of nonexistent nodes/resources
- silent reinterpretation of approval status
- output outside the declared structured contract

## 5. Output Formatting Rule

Structured output must remain machine-checkable.
Preferred form:
- JSON-like structured object
- deterministic field names
- no prose-only output when a structured contract is required

## 6. Relationship to Other Docs

Normative inputs:
- `designer_session_state_card.md`
- `semantic_intent_contract.md`
- `grounded_intent_contract.md`
- `designer_intent_contract.md`
- `circuit_patch_contract.md`

## 7. Decision

The operational prompt is a runtime envelope for existing Designer contracts.
It must stay subordinate to the contract layer.
