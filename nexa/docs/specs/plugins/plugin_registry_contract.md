# Plugin Registry Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_registry_contract.md`

## 1. Purpose

This document defines the canonical registry contract for plugins in Nexa.

It establishes:
- what the plugin registry is
- what a registry entry represents
- how a runtime artifact becomes registry-visible
- how publication scope is represented
- how registry state differs from builder state and runtime state
- how future users, reviewers, and AI systems can discover and reason about available plugins safely

## 2. Core Decision

1. The registry is the canonical catalog of publishable plugin artifacts.
2. A plugin runtime artifact and a registry entry are related but not identical.
3. Publication into the registry must preserve artifact identity, manifest identity, policy posture, verification posture, and publication scope.
4. Registry presence does not erase builder provenance.
5. Runtime may use registry entries for discovery, but runtime trust still depends on builder-governed and policy-governed conditions.

## 3. Non-Negotiable Boundaries

- Proposal boundary
- Builder boundary
- Artifact boundary
- Runtime boundary
- Trust boundary

## 4. Registry Model Overview

The canonical registry layer contains:
1. Registry entries
2. Registry indexing/search metadata
3. Publication scope metadata
4. Visibility/governance metadata
5. Registry lifecycle state

The registry catalogs plugin artifacts. It does not redefine plugin code.

## 5. Canonical Registry Entry Concept

PluginRegistryEntry must:
- refer to exactly one canonical plugin artifact
- refer to exactly one canonical manifest identity
- preserve artifact provenance and publication state
- expose publication scope explicitly
- preserve policy and verification posture summaries
- be independently discoverable without loading raw artifact code

## 6. Canonical Registry Entry Structure

PluginRegistryEntry
- registry_entry_id: string
- plugin_id: string
- artifact_ref: string
- manifest_ref: string
- registry_version: string
- publication_status: enum("draft", "published", "suspended", "deprecated", "withdrawn")
- publication_scope: enum("local_private", "workspace_shared", "internal_shared", "other")
- visibility_metadata: PluginRegistryVisibilityMetadata
- registry_summary: PluginRegistrySummary
- policy_posture: PluginRegistryPolicyPosture
- verification_posture: PluginRegistryVerificationPosture
- provenance_summary: PluginRegistryProvenanceSummary
- governance_metadata: PluginRegistryGovernanceMetadata
- timestamps: PluginRegistryTimestamps

## 7. Summary, Visibility, and Posture

Registry summary should expose:
- plugin name
- category
- summary
- keywords
- side-effect mode
- intended use summary

Visibility metadata must distinguish:
- visibility scope
- search discoverability
- installability

Registry policy posture and verification posture must remain explicit and queryable.

## 8. Provenance and Governance

The registry must preserve:
- builder request/result refs
- proposal ref if available
- artifact version
- build timestamp
- review metadata
- suspension/deprecation reasons
- historical timestamps

## 9. Lifecycle States

Registry states:
- draft
- published
- suspended
- deprecated
- withdrawn

Publication does not imply installation or runtime activation.

## 10. Publication Rules

Publication requires at minimum:
- canonical runtime artifact
- canonical manifest
- explicit publication scope
- explicit policy posture
- explicit verification posture
- explicit provenance summary

Otherwise publication must fail or remain draft.

## 11. Search and Discovery Rules

Registry should support discovery by:
- plugin name
- category
- keyword
- scope
- side-effect mode
- readiness posture
- policy sensitivity

Search must return registry entries, not raw artifact internals.

## 13. Installation / Consumption Rules

Registry may expose installation or enablement actions later, but:
- installation eligibility must remain explicit
- publication visibility does not imply installation permission
- runtime trust checks may still apply after registry selection
- registry selection must not bypass policy and verification rules

## 14. Explicitly Forbidden Registry Patterns

- proposal-only publication
- policy-blind publication
- verification ambiguity
- scope ambiguity
- silent historical erasure
- artifact/entry identity collapse

## 15. Canonical Summary

- The registry is the canonical discovery and publication layer for plugin artifacts.
- A registry entry is not the same thing as a proposal, a builder result, or the runtime artifact itself.
- Publication scope, policy posture, verification posture, and provenance must remain explicit.
- Registry publication must not blur trust, readiness, or policy boundaries.

## 16. Final Statement

A plugin should not become “published” merely because it exists.

It becomes registry-visible only when its artifact identity, publication scope, posture, and provenance are made explicit through a canonical registry entry.

That is the canonical meaning of Plugin Registry in Nexa.
