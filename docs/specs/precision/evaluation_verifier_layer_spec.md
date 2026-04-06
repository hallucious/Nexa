# Evaluation / Verifier Layer Spec v0.1

## Recommended save path
`docs/specs/precision/evaluation_verifier_layer_spec.md`

## 1. Purpose

This document defines the official Evaluation / Verifier Layer for Nexa.

Its purpose is to standardize how Nexa judges whether an output is:

- structurally valid
- logically coherent
- requirement-complete
- policy-safe
- evidence-supported
- good enough to continue, retry, escalate, or stop

This layer is the main quality-control extension of the precision track.

## 2. Core Decision

Nexa must not treat node success as equivalent to output quality.

Official rule:

- execution success and quality success are different states
- quality must be judged explicitly
- verifier outcomes must be structured, not implied

In short:

a node may execute successfully and still fail verification

## 3. Position in Architecture

Canonical position:

Execution Resource
→ raw output
→ verifier layer
→ verification findings / score / decision signal
→ retry / branch / escalate / continue

The verifier layer is engine-facing.
UI may show it, but UI does not define it.

## 4. Core Principles

1. verification is explicit
2. verification results are structured
3. different verifier modes may coexist
4. verifier output must be machine-actionable
5. verifier results must be traceable
6. verifier policy must be configurable
7. verifier must not silently rewrite node truth

## 5. Supported Verification Modes

### 5.1 Structural Verification
Checks:
- schema validity
- required field presence
- type mismatches
- enum / list / object shape mismatches

### 5.2 Logical Verification
Checks:
- internal contradiction
- invalid reasoning chain markers
- unsupported conclusions
- broken implication structure

### 5.3 Requirement Verification
Checks:
- missing requested sections
- incomplete objective fulfillment
- constraint violations
- output format mismatch

### 5.4 Policy Verification
Checks:
- restricted content
- unsafe instructions
- permission boundary violations
- tool/plugin misuse

### 5.5 Evidence Verification
Checks:
- missing evidence
- weak grounding
- evidence diversity problems
- unsupported confidence

## 6. Canonical Result Object

VerifierResult
- verifier_id: string
- verifier_type: enum(
    "structural",
    "logical",
    "requirement",
    "policy",
    "evidence",
    "composite"
  )
- target_ref: string
- status: enum("pass", "warning", "fail", "inconclusive")
- score: optional float
- confidence: optional float
- reason_code: string
- findings: list[VerifierFinding]
- retry_advice: RetryAdvice
- branch_advice: BranchAdvice
- escalation_advice: EscalationAdvice
- explanation: string

VerifierFinding
- finding_id: string
- severity: enum("info", "warning", "error", "critical")
- category: string
- reason_code: string
- message: string
- evidence_refs: list[string]
- suggested_action: optional string

## 7. Composite Verification

Nexa may run multiple verifiers on the same output.

CompositeVerifierResult
- target_ref
- constituent_results: list[VerifierResult]
- aggregate_status
- aggregate_score
- aggregate_confidence
- blocking_reason_codes
- recommended_next_step

Aggregation rules:
- critical fail dominates
- policy fail dominates normal quality pass
- inconclusive must remain visible
- missing evidence must lower aggregate confidence

## 8. Retry / Branch / Escalation Coupling

Verifier results may drive downstream behavior.

### Retry
Allowed when:
- issue is likely prompt-fixable
- issue is likely model-fixable
- issue is not a hard policy block

### Branch
Allowed when:
- multiple plausible repairs exist
- confidence is low but not hopeless
- comparison between alternatives is valuable

### Escalation
Allowed when:
- policy boundary is involved
- repeated retry failed
- confidence remains below threshold
- human review is mandatory

## 9. Reason Code Taxonomy

Every fail or warning result must include a stable `reason_code`.

Minimum categories:

- STRUCTURE_*
- LOGIC_*
- REQUIREMENT_*
- POLICY_*
- EVIDENCE_*
- ROUTING_*
- UNKNOWN_*

Reason codes must be stable enough for analytics and memory reuse.

## 10. Engine Rules

The verifier layer must:

- emit traceable structured results
- preserve raw output separately
- avoid mutating the raw producer output
- support later replay and diff
- support score thresholds without hiding detailed findings

## 11. First Implementation Scope

The first implementation should support:

- structural verifier
- requirement verifier
- logical verifier (minimal)
- composite aggregator
- reason_code registry
- retry coupling
- trace persistence of verifier output

## 12. Non-Goals for v0.1

Not required in the first implementation:

- universal truth engine
- unrestricted external fact-checking
- self-modifying verifier policies
- full benchmark-scale calibration
- automatic verifier-generated patch commit

## 13. Final Decision

The Evaluation / Verifier Layer is the official quality-control boundary of the precision track.

It turns Nexa from:
"resource executed successfully"

into:
"resource executed, was judged, and produced a structured quality decision"
