# Designer Validator Precheck Contract v0.1

## 1. Purpose

This contract defines the precommit validation boundary for Designer AI proposals.

It answers:
1. Is the proposed future state valid enough to continue?
2. What is missing, ambiguous, unsafe, or too expensive?
3. What must be shown before approval?
4. What must block commit?

## 2. Core Principles

1. Precheck is mandatory for create/modify/repair/optimize.
2. Precheck evaluates the proposed future state.
3. Precheck produces structured findings, not only pass/fail.
4. Precheck distinguishes blocking issues, warnings, and confirmation-required risks.
5. Precheck must not silently repair the proposal.

## 3. ValidationPrecheck Schema

```text
ValidationPrecheck
- precheck_id
- patch_ref
- intent_ref
- evaluated_scope
- overall_status: pass | pass_with_warnings | confirmation_required | blocked
- structural_validity
- dependency_validity
- input_output_validity
- provider_resolution
- plugin_resolution
- safety_review
- cost_assessment
- ambiguity_assessment
- preview_requirements
- blocking_findings
- warning_findings
- confirmation_findings
- recommended_next_actions
- explanation
```

## 4. Major Report Areas

- Structural validity
- Dependency validity
- Input/output validity
- Provider resolution
- Plugin resolution
- Safety review
- Cost assessment
- Ambiguity assessment

## 5. Overall Status Semantics

- `pass`: no blocking issue
- `pass_with_warnings`: non-critical concerns only
- `confirmation_required`: no blocking issue, but explicit user confirmation needed
- `blocked`: commit forbidden

## 6. Blocking Conditions

Examples:
- missing required final output
- unresolved required input
- provider not found
- forbidden plugin/provider
- unsupported structural cycle
- high-risk flow without required review gate

## 7. Confirmation Conditions

Examples:
- destructive edit
- broad-scope change
- critical provider replacement
- output semantics materially changed
- multiple structurally valid interpretations
- significant cost/complexity increase

## 8. Decision

Designer AI may propose.
Patch may describe.
Precheck must judge.
If blocking findings remain unresolved, commit is forbidden.
