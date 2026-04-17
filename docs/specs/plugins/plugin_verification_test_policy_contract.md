# Plugin Verification / Test Policy Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_verification_test_policy_contract.md`

## 1. Purpose

This document defines the canonical verification and test policy contract for plugins in Nexa.

It establishes:
- what verification means for a plugin
- how verification differs from validation
- what minimum checks are required before a plugin can be treated as build-complete
- how verification outcomes must be recorded
- how runtime, registry, and future review systems interpret verification posture

## 2. Core Decision

1. Validation and verification are not the same thing.
2. Validation checks contract and policy correctness.
3. Verification checks whether the candidate behaves acceptably enough to be trusted within its intended scope.
4. Verification posture must be explicit, machine-readable, and preserved across artifact and registry layers.
5. A plugin must not be treated as fully trusted merely because it was generated successfully.

## 3. Non-Negotiable Boundaries

- Proposal boundary
- Builder boundary
- Runtime boundary
- Registry boundary
- Trust boundary

## 4. Core Vocabulary

- Validation
- Verification
- Verification Profile
- Verification Evidence
- Verification Posture

## 5. Verification Model Overview

Four layers:
1. verification requirements
2. executed checks
3. verification evidence
4. verification posture

## 6. Canonical Verification Requirements Object

PluginVerificationRequirements
- required_profile: enum("light", "standard", "strict")
- require_static_load_check: bool
- require_smoke_execution: bool
- require_io_contract_check: bool
- require_template_integrity_check: bool
- require_policy_alignment_check: bool
- require_behavioral_test: bool
- require_negative_scope_test: bool
- additional_requirements: list[string]

## 7. Canonical Verification Evidence Object

PluginVerificationEvidence
- verification_run_id: string
- artifact_ref: string
- executed_profile: string
- executed_checks: list[VerificationCheckResult]
- started_at: string
- completed_at: string
- overall_result: enum("passed", "failed", "partial")
- notes: string | null

Check families include:
- static_load
- smoke_execution
- io_contract
- template_integrity
- policy_alignment
- behavioral_test
- negative_scope_test

## 8. Canonical Verification Posture Object

PluginVerificationPosture
- verification_status: enum("not_verified", "verified", "verification_failed", "partially_verified")
- verification_profile: string | null
- passed_check_count: int
- failed_check_count: int
- skipped_check_count: int
- blocking_failures_present: bool
- posture_notes: string | null

## 9. Minimum Verification Check Families

At minimum:
- Static Load Check
- Smoke Execution Check
- I/O Contract Check
- Template Integrity Check
- Policy Alignment Check
- Behavioral Test
- Negative Scope Test

## 10. Verification Profiles

### light
For early private or exploratory candidates.

### standard
For normal internal ready-to-use plugins.

### strict
For higher-trust or broader-scope publication.

## 11. Failure Semantics

The system must distinguish:
- failed but retryable
- failed and blocking
- skipped because not applicable
- skipped but still required by target posture

`validated` must never be interpreted as `verified`.

## 12. Relationships

Manifest and registry may expose verification posture, but must not invent it. Runtime may consume verification posture for preflight acceptance logic.

## 13. Canonical Findings Categories

Examples:
- VERIFY_STATIC_LOAD_FAILED
- VERIFY_SMOKE_EXECUTION_FAILED
- VERIFY_IO_CONTRACT_MISMATCH
- VERIFY_TEMPLATE_INTEGRITY_FAILED
- VERIFY_POLICY_ALIGNMENT_FAILED
- VERIFY_BEHAVIORAL_TEST_FAILED
- VERIFY_NEGATIVE_SCOPE_TEST_FAILED
- VERIFY_REQUIRED_CHECK_SKIPPED

## 14. Explicitly Forbidden Verification Patterns

- verified-by-default
- validation-is-verification collapse
- hidden skipped checks
- registry-only verification claims
- manifest-only verification claims

## 15. Canonical Summary

- Verification is a distinct trust-bearing stage after validation.
- Validation and verification are not interchangeable.
- Verification must be evidence-based, profile-based, and machine-readable.
- Artifact manifests and registry entries may summarize posture, but they must not invent it.

## 16. Final Statement

A plugin is not trustworthy merely because it exists, builds, or validates.

It becomes trustworthy only to the extent that its behavior has been explicitly verified under a defined policy and recorded as evidence.

That is the canonical meaning of Plugin Verification / Test Policy in Nexa.
