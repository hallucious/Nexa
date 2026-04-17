# Plugin Runtime Governance Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_runtime_governance_contract.md`

## 1. Purpose

This document defines the canonical runtime governance contract for plugins in Nexa.

It establishes:
- how runtime evidence influences plugin operational posture
- how plugins are allowed, limited, promoted, quarantined, suspended, or removed
- how governance decisions consume verification posture, failure history, observability evidence, and policy posture
- how local runtime operation remains safe over time rather than only at install time
- how governance decisions are recorded as explicit engine truth

## 2. Core Decision

1. Runtime trust is not a one-time decision.
2. Runtime governance must consume accumulated execution evidence.
3. Governance decisions must remain explicit and traceable.
4. Governance must distinguish activation eligibility, continued active eligibility, scope eligibility, and quarantine/suspension/removal posture.
5. Governance must not silently widen plugin authority or visibility.
6. Governance must remain downstream of builder truth and runtime evidence.

## 3. Non-Negotiable Boundaries

- Builder boundary
- Policy boundary
- Runtime boundary
- Trace boundary
- Activation boundary

## 4. Core Vocabulary

- Governance Posture
- Promotion
- Restriction
- Suspension
- Quarantine
- Removal
- Governance Evidence

## 5. Canonical Lifecycle Position

Verified / Installed / Active Plugin
-> Runtime Evidence Accumulation
-> Governance Evaluation
-> Governance Decision
-> Posture Update
-> Continued Runtime Use or Restriction

## 6. Canonical Governance Posture Object

PluginRuntimeGovernancePosture
- governance_posture_id: string
- plugin_id: string
- target_runtime_ref: string
- artifact_ref: string
- manifest_ref: string
- current_posture: enum(
    "active_allowed",
    "active_limited",
    "review_required",
    "suspended",
    "quarantined",
    "removed"
  )
- trust_scope: enum("local_private_only", "workspace_limited", "runtime_local", "internal_shared", "other")
- evidence_ref_set: list[string]
- last_evaluated_at: string
- last_decision_ref: string | null
- notes: string | null

## 7. Canonical Governance Decision Object

PluginRuntimeGovernanceDecision
- decision_id: string
- plugin_id: string
- target_runtime_ref: string
- decision_type: enum(
    "maintain",
    "promote",
    "restrict",
    "require_review",
    "suspend",
    "quarantine",
    "remove",
    "restore"
  )
- previous_posture: string
- new_posture: string
- decision_basis: PluginGovernanceDecisionBasis
- decided_at: string
- decided_by: string
- notes: string | null

## 8. Governance Evidence Inputs

Governance must consume explicit evidence such as:
- verification posture
- approved namespace policy posture
- failure history
- recovery history
- runtime observability summaries
- repeated timeout/cancellation patterns
- policy violation attempts
- artifact/output integrity signals
- human review decisions where applicable

## 9. Governance Decision Families

- Maintain
- Promote
- Restrict
- Require Review
- Suspend
- Quarantine
- Remove
- Restore

## 10. Promotion, Restriction, Suspension, Quarantine, Removal, Restore Rules

These decisions must be explicit and grounded in evidence. Promotion requires acceptable verification, stability, and absence of serious violations. Restriction narrows use without full suspension. Suspension blocks active use. Quarantine is stronger, for suspected unsafe or unstable behavior. Removal ends local runtime eligibility. Restore requires explicit justification and does not erase prior history.

## 11. Relationships

- Failure / Recovery provides evidence.
- Observability provides evidence.
- Loading / Installation defines initial acceptance.
- Registry publication remains distinct from runtime-local governance posture.

## 12. Canonical Governance Findings Categories

Examples:
- GOV_MAINTAINED
- GOV_PROMOTED
- GOV_RESTRICTED
- GOV_REVIEW_REQUIRED
- GOV_SUSPENDED
- GOV_QUARANTINED
- GOV_REMOVED
- GOV_RESTORED
- GOV_FAILURE_RATE_EXCEEDED
- GOV_POLICY_VIOLATION_OBSERVED

## 13. Explicitly Forbidden Patterns

- silent posture drift
- failure-blind governance
- observability-free governance
- policy-loosening by convenience
- publication/runtime collapse
- history erasure

## 14. Canonical Summary

- Runtime trust is ongoing, not one-time.
- Governance decisions must consume explicit runtime evidence.
- Plugins may be maintained, promoted, restricted, suspended, quarantined, removed, or restored.
- Governance posture must remain distinct from registry publication and installation truth.

## 15. Final Statement

A plugin in Nexa should not remain trusted forever simply because it was once verified and installed.

It should continue to earn runtime trust through explicit governance decisions grounded in real execution evidence.

That is the canonical meaning of Plugin Runtime Governance in Nexa.
