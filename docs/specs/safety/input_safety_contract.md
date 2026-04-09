# Input Safety Contract

## Recommended save path
`docs/specs/safety/input_safety_contract.md`

## 1. Purpose

This document defines the canonical input-safety contract for Nexa when engine-level contract changes are allowed.

Its purpose is to prevent unsafe, accidental, or policy-disallowed input from entering execution without explicit inspection and decision boundaries.

This contract exists because general-user risk often begins before execution:
- sensitive personal data pasted by mistake
- confidential document ingestion without awareness
- disallowed content sent into provider APIs
- unsafe automation payloads entering unattended runs

Input safety must therefore become an explicit pre-execution contract,
not a late error or hidden provider rejection.

## 2. Core Decision

Input must be safety-evaluated before execution begins.

Official rule:

- input safety is a pre-execution boundary
- safety findings must be structured, not purely textual
- blocking and warning states must be distinguished
- input safety must not be reduced to provider-side failure only
- users must be able to understand what is blocked, why, and what next action is available

In short:

Nexa input safety is an explicit gate on what enters execution.

## 3. Non-Negotiable Boundaries

The following must remain unchanged:

- Node remains the sole execution unit
- dependency-based execution remains the runtime rule
- execution truth remains engine-owned
- UI does not fabricate safety truth
- safety findings do not silently mutate user input
- blocked input must not be executed through hidden fallback paths

This contract may add pre-execution safety evaluation,
but it must not become an invisible content-rewriting system.

## 4. Safety Lifecycle

Canonical lifecycle:

Input Received
-> Input Classification
-> Sensitive / Restricted Pattern Detection
-> Policy Evaluation
-> Safety Decision
-> Block / Warn / Allow
-> Optional User Confirmation
-> Execution Launch

## 5. Contract Family Overview

This contract family contains five conceptual layers:

1. Input Classification Contract
2. Safety Finding Contract
3. Safety Decision Contract
4. Confirmation Boundary Contract
5. Safety Record Contract

## 6. Input Classification Contract

### 6.1 Purpose
Input classification describes what kind of material is about to enter execution.

### 6.2 Canonical input classification object

InputClassification
- input_ref: string
- input_type: enum(
    "plain_text",
    "structured_text",
    "file",
    "image",
    "url",
    "external_payload",
    "unknown"
  )
- contains_personal_data: bool
- contains_sensitive_business_data: bool
- contains_credentials_or_secrets: bool
- contains_policy_sensitive_content: bool
- confidence: enum("low", "medium", "high")

### 6.3 Rules
- classification may be imperfect, but confidence must be explicit
- secret/credential-like patterns must be surfaced distinctly
- file/url inputs must remain classifiable without pretending full semantic certainty

## 7. Safety Finding Contract

### 7.1 Purpose
Safety findings explain what risk was detected.

### 7.2 Canonical safety finding object

InputSafetyFinding
- finding_id: string
- input_ref: string
- severity: enum("info", "warning", "blocking")
- category: enum(
    "credential_exposure",
    "personal_data",
    "confidential_data",
    "policy_sensitive_content",
    "unsafe_automation_input",
    "unknown_risk",
    "other"
  )
- reason_code: string
- human_summary: string
- suggested_next_action: optional string

### 7.3 Rules
- findings must be structured
- human_summary must be understandable to non-experts
- warning and blocking findings must not be collapsed together
- reason_code must remain machine-usable

## 8. Safety Decision Contract

### 8.1 Purpose
Safety decisions determine whether execution may proceed.

### 8.2 Canonical safety decision object

InputSafetyDecision
- decision_id: string
- input_ref: string
- overall_status: enum("allow", "allow_with_warning", "confirmation_required", "blocked")
- finding_refs: list[string]
- confirmation_required: bool
- provider_restrictions: optional list[object]
- launch_allowed: bool

### 8.3 Rules
- blocked means launch must not proceed
- confirmation_required must remain distinct from warning-only
- provider restrictions may narrow execution routing without silently changing user intent
- launch decisions must be explicit engine truth

## 9. Confirmation Boundary Contract

### 9.1 Purpose
Some input should not be hard-blocked, but should still require explicit acknowledgment.

### 9.2 Canonical confirmation object

InputSafetyConfirmationBoundary
- boundary_id: string
- decision_ref: string
- requires_user_confirmation: bool
- confirmation_basis: list[string]
- confirmed_by: optional string
- confirmed_at: optional string

### 9.3 Rules
- confirmation must be explicit
- mere visibility of a warning is not confirmation
- automation paths must not treat missing confirmation as implicit approval

## 10. Safety Record Contract

### 10.1 Purpose
Input safety must remain traceable after execution or blocking.

### 10.2 Canonical safety record object

InputSafetyRecord
- input_ref: string
- classification_ref: string
- decision_ref: string
- finding_refs: list[string]
- final_status: enum("allowed", "allowed_with_warning", "confirmed_then_allowed", "blocked")
- recorded_at: string

### 10.3 Rules
- blocked inputs must still be recordable
- safety record must remain linked to run launch decisions where applicable
- later audit must be able to explain why execution was allowed or blocked

## 11. File and URL Inputs

This contract must support file and URL inputs explicitly.

Minimum rules:
- files must be classifiable before provider submission
- URL inputs must be evaluated as external sources, not trusted by default
- large external inputs may trigger warning or confirmation boundaries
- the engine must not silently fetch and execute high-risk external content without safety evaluation

## 12. Relationship to Provider and UI

Provider-side rejections do not replace input safety.
UI-side wording does not define safety truth.

The engine must:
- evaluate input safety before launch
- expose structured findings
- let UI render beginner-safe explanations
- preserve machine-usable reason codes and decision states

## 13. Relationship to Automation

Automation increases safety risk because runs may start unattended.

Therefore:
- unattended trigger paths must still respect input safety
- blocked automation input must stop before execution
- confirmation-required input must not auto-run unless an explicit prior policy permits it

## 14. Explicit Non-Goals

This v1 contract does not define:
- full legal compliance policy by jurisdiction
- downstream provider moderation internals
- full redaction/transformation policy
- UI rendering implementation details
- destination-side outbound safety rules

## 15. Final Statement

Input safety in Nexa must be an explicit pre-execution gate.

Unsafe or sensitive input must not slide into execution by accident,
and safety must remain explainable as structured engine truth rather than vague provider failure.