# Plugin Lifecycle State Machine Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_lifecycle_state_machine_contract.md`

## 1. Purpose

This document defines the canonical lifecycle state machine contract for plugins in Nexa.

It establishes:
- the official lifecycle states for a plugin
- the official transitions between those states
- which transitions are valid, invalid, or terminal
- how builder, registry, runtime, failure, observability, and governance states relate
- how future runtime, UI, analytics, and governance layers can share one lifecycle vocabulary

## 2. Core Decision

1. Plugin lifecycle must be modeled as an explicit state machine.
2. Lifecycle states must remain machine-readable.
3. State transitions must be governed by canonical upstream truth.
4. Publication, installation, activation, execution, failure, and governance must remain distinguishable domains.
5. A plugin must not appear to be in mutually contradictory states.
6. Lifecycle transitions must remain traceable and historically visible.

## 3. Lifecycle State Domains

The official lifecycle model has six domains:
1. Build Domain
2. Publication Domain
3. Installation Domain
4. Binding Domain
5. Execution Domain
6. Governance Domain

## 4. Build Domain States

- proposed
- intake_ready
- builder_normalized
- scaffold_generated
- validation_failed
- verification_failed
- build_complete_unregistered
- registered

## 5. Publication Domain States

- registry_draft
- registry_published
- registry_suspended
- registry_deprecated
- registry_withdrawn

## 6. Installation Domain States

- not_installable
- installable
- installed
- install_failed
- removed

## 7. Binding Domain States

- not_bound
- binding_ready
- bound_ready
- binding_failed
- bound_suspended

## 8. Execution Domain States

- execution_idle
- execution_queued
- execution_running
- execution_partial
- execution_completed
- execution_failed
- execution_cancelled
- execution_timed_out

Execution states are per execution instance, not long-lived posture.

## 9. Governance Domain States

- active_allowed
- active_limited
- review_required
- suspended
- quarantined
- governance_removed
- restored

## 10. Canonical Unified Lifecycle Object

PluginLifecycleState
- lifecycle_state_id: string
- plugin_id: string
- artifact_ref: string | null
- manifest_ref: string | null
- target_runtime_ref: string | null
- build_state: string | null
- publication_state: string | null
- installation_state: string | null
- binding_state: string | null
- current_execution_state: string | null
- governance_state: string | null
- last_transition_ref: string | null
- last_updated_at: string
- notes: string | null

## 11. Canonical Transition Object

PluginLifecycleTransition
- transition_id: string
- plugin_id: string
- from_state_domain: string
- from_state: string | null
- to_state_domain: string
- to_state: string
- trigger_type: enum(
    "builder_result",
    "registry_decision",
    "installation_decision",
    "binding_decision",
    "execution_event",
    "failure_event",
    "recovery_event",
    "governance_decision",
    "manual_admin_action",
    "unknown"
  )
- trigger_ref: string | null
- occurred_at: string
- rationale_summary: string | null

## 12. Core Transition Principles

Examples:
- proposed -> intake_ready -> builder_normalized -> scaffold_generated -> build_complete_unregistered -> registered
- registry_draft -> registry_published
- installable -> installed
- not_bound -> binding_ready -> bound_ready
- execution_idle -> execution_running -> execution_completed/failed/cancelled/timed_out
- active_allowed -> restricted/suspended/quarantined/removed/restored

Different domains interact, but one domain must not silently overwrite another.

## 13. Cross-Domain Principles

- Registered does not imply installed.
- Installed does not imply bound.
- Bound does not imply execution success.
- Execution failure does not automatically imply governance removal.
- Governance suspension does not rewrite publication state.

## 14. Canonical Legality Rules

A lifecycle snapshot must satisfy:
- build_state internally consistent
- publication_state not contradicting build_state
- installation_state not implying unavailable artifact identity
- binding_state not implying unavailable prerequisites
- execution_state not existing without binding/runtime context
- governance_state explicit where runtime control is applied

## 15. Canonical Impossible Combinations

Forbidden examples:
- verification_failed + active_allowed
- not_installable + installed
- not_bound + execution_running
- governance_removed + active_allowed

## 16. Historical Recording Rules

Lifecycle transitions must be historically preserved. The system must answer:
- what state existed at a given time
- what transitions occurred before/after
- what triggered each transition
- whether restoration followed suspension/quarantine/removal

## 17. Relationship to Observability and Governance

Observability provides evidence. Governance changes governance-domain states. This lifecycle contract integrates those domains into one canonical machine.

## 18. Canonical Findings Categories

Examples:
- LIFECYCLE_BUILD_ADVANCED
- LIFECYCLE_PUBLICATION_CHANGED
- LIFECYCLE_INSTALLATION_CHANGED
- LIFECYCLE_BINDING_CHANGED
- LIFECYCLE_EXECUTION_CHANGED
- LIFECYCLE_GOVERNANCE_CHANGED
- LIFECYCLE_INVALID_TRANSITION_ATTEMPT
- LIFECYCLE_IMPOSSIBLE_STATE_COMBINATION

## 19. Explicitly Forbidden Patterns

- flag soup
- domain collapse
- UI-defined lifecycle
- silent cross-domain overwrites
- history erasure

## 20. Canonical Summary

- Plugin lifecycle must be modeled as an explicit state machine.
- Build, publication, installation, binding, execution, and governance are distinct domains.
- Cross-domain relationships must be explicit and non-contradictory.
- State transitions must be triggered by canonical evidence and preserved historically.

## 21. Final Statement

A plugin in Nexa should not live as a vague combination of “maybe published, maybe active, maybe failing.”

It should move through one explicit lifecycle state machine whose domains, transitions, and history remain clear to runtime, UI, governance, and future AI readers.

That is the canonical meaning of Plugin Lifecycle State Machine in Nexa.
