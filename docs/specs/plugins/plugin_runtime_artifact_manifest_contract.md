# Plugin Runtime Artifact / Manifest Contract v1.0

## Recommended save path
`docs/specs/plugins/plugin_runtime_artifact_manifest_contract.md`

## 1. Purpose

This document defines the canonical runtime artifact and manifest contract for plugins in Nexa.

It establishes:
- what a built plugin candidate physically consists of
- what manifest data must exist
- how the runtime artifact is separated from proposal objects
- how approved namespace policy is linked into the artifact
- how Builder, Runtime, Registry, and future review systems can all refer to the same plugin artifact consistently

## 2. Core Decision

1. A plugin runtime artifact is the build-stage output of the Plugin Builder.
2. A plugin runtime artifact is not the same thing as a Designer proposal.
3. A plugin runtime artifact must carry a manifest explicit enough for validation, verification, registry publication, runtime loading, and audit/review.
4. Manifest presence does not by itself grant trust.
5. Runtime loading must depend on builder-governed approval state, not manifest prose alone.

## 3. Non-Negotiable Boundaries

- Proposal boundary
- Builder boundary
- Runtime boundary
- Savefile boundary
- Trust boundary

## 4. Artifact Model Overview

The canonical runtime plugin artifact has two inseparable layers:
1. Runtime package contents
2. Manifest

Both are required.

## 5. Canonical Artifact Identity

PluginRuntimeArtifact must:
- be produced by the Plugin Builder
- have one canonical manifest
- contain runtime-loadable plugin implementation material
- carry explicit identity/version metadata
- reference approved namespace policy
- declare expected input/output contract summaries

## 6. Canonical Top-Level Artifact Structure

PluginRuntimeArtifact
- artifact_id: string
- artifact_version: string
- build_ref: string
- manifest: PluginArtifactManifest
- package_layout: PluginPackageLayout
- integrity: PluginIntegrityMetadata
- provenance: PluginProvenanceMetadata

## 7. Plugin Package Layout

PluginPackageLayout
- entrypoint_module: string
- entrypoint_symbol: string
- source_files: list[string]
- support_files: list[string]
- test_files: list[string]
- manifest_path: string
- packaging_format: enum("directory", "bundle", "other")

Runtime must not need to guess the entrypoint.

## 8. Plugin Manifest

PluginArtifactManifest
- manifest_version: string
- plugin_id: string
- plugin_name: string
- plugin_display_name: string | null
- plugin_category: string
- plugin_type: string | null
- plugin_summary: string
- plugin_description: string | null
- artifact_version: string
- builder_spec_version: string
- runtime_contract_version: string
- entrypoint: { module, symbol }
- execution_mode: enum(
    "deterministic_component",
    "bounded_external_read",
    "bounded_external_write",
    "mixed"
  )
- input_contract_summary: PluginArtifactManifestInputSummary
- output_contract_summary: PluginArtifactManifestOutputSummary
- approved_namespace_policy_ref: string
- side_effect_summary: PluginSideEffectSummary
- dependency_summary: PluginDependencySummary
- verification_summary: PluginVerificationSummary
- compatibility: PluginCompatibilitySummary
- registry_readiness: PluginRegistryReadinessSummary
- manifest_notes: string | null

The manifest is mandatory.

## 9. Summary Sections

The manifest must summarize:
- input expectations
- output expectations
- side effects
- dependencies
- verification posture
- compatibility
- registry readiness

These are runtime-facing summaries, not a duplication of full intake drafts.

## 10. Provenance and Integrity

PluginProvenanceMetadata
- proposal_ref: string | null
- builder_request_ref: string
- builder_result_ref: string
- produced_by_builder_version: string
- build_timestamp: string
- produced_from_template_family: string | null

PluginIntegrityMetadata
- manifest_hash: string | null
- package_hash: string | null
- integrity_mode: enum("none", "basic_hash", "strong_hash")
- notes: string | null

## 11. Relationship to Current Codebase Manifest Names

The existing codebase already uses `PluginManifest` names in other platform/plugin contexts.

Therefore this contract intentionally uses `PluginArtifactManifest` for the artifact-level manifest defined here.

This naming rule exists to avoid three-way ambiguity between:
- existing discovery/platform manifest shapes in code
- existing version-registry manifest shapes in code
- the new artifact-level manifest defined by this contract

This document does not claim those existing manifest families have already been merged.
Coexistence and migration remain explicit future work.

## 12. Relationship to Current Plugin Vocabulary

This contract may use `plugin_category` as an artifact-summary classification field.
That field must not be silently merged with existing current-code `plugin_type` fields.

Canonical distinction:
- `plugin_category` = builder/artifact purpose class
- `plugin_type` = current runtime/platform role class

Normative bridge rule:
- `plugin_category` must not be treated as a synonym for `plugin_type`
- a runtime-usable artifact must expose or resolve an explicit runtime-facing `plugin_type` before loading/install acceptance
- that runtime-facing type may be carried directly in the artifact/manifest layer or resolved by a declared loading/install rule
- category alone is not sufficient to determine runtime/plugin-role behavior

## 13. Relationship to Current Codebase Alignment

This document defines the target artifact contract family.
It should be read as partially aligned / migration-required rather than fully identical to current code structures.

Implementation work must bridge from current discovery, loader, registry, and manifest code into this artifact-level contract shape explicitly.

## 14. Relationship to Namespace Policy

The manifest must reference approved namespace policy explicitly through:
- approved_namespace_policy_ref

Manifest presence does not replace runtime enforcement.

## 15. Runtime Loading Rules

Runtime must check before loading:
- manifest presence
- entrypoint resolution
- compatibility
- namespace policy reference
- verification posture
- dependency posture

## 16. Explicitly Forbidden Artifact Patterns

- manifestless executable plugin
- multiple conflicting manifests
- guessable entrypoint only
- false verification claims
- policy-free side-effectful plugin
- registry-readiness fabrication

## 17. Extensibility and Efficiency

Builder, runtime, and registry should share one canonical manifest family. Manifest should summarize validated truth rather than duplicate every draft object.

## 18. Canonical Summary

- The Plugin Runtime Artifact is the canonical built plugin package.
- The Plugin Manifest is the canonical machine-readable identity and contract summary.
- The manifest is mandatory but does not itself grant trust.
- Approved namespace policy must be linked explicitly.

## 19. Final Statement

A plugin in Nexa should not become “whatever files happened to be generated.”

It must become one explicit, canonical runtime artifact with one explicit, canonical manifest.

That is the canonical meaning of Plugin Runtime Artifact / Manifest in Nexa.
