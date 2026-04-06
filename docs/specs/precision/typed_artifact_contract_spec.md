# Typed Artifact Contract Spec v0.1

## Recommended save path
`docs/specs/precision/typed_artifact_contract_spec.md`

## 1. Purpose

This document defines the official Typed Artifact Contract for Nexa.

Its purpose is to make node inputs, node outputs, and produced artifacts:

- typed
- versioned
- validator-checkable
- transformable
- trace-linkable
- stable across larger circuits

This contract prevents loose output blobs from destabilizing the engine.

## 2. Core Decision

Nexa must not treat arbitrary dict-like output as a sufficient long-term contract.

Official rule:

- every meaningful produced artifact must have a declared type
- artifact types must have versioned schemas
- transforms between artifact types must be explicit

## 3. Position in Architecture

Producer Node
→ Typed Artifact
→ schema validation
→ optional transform
→ downstream consumer

Typed artifacts sit between execution and downstream use.

## 4. Core Principles

1. artifact types are explicit
2. artifact schemas are versioned
3. producer and consumer contracts must match
4. transform nodes are first-class
5. artifacts remain append-only in meaning
6. raw output and normalized artifact may coexist
7. version drift must be visible

## 5. Canonical Artifact Type Families

Initial canonical types:

- `text`
- `json_object`
- `decision`
- `critique`
- `evidence_set`
- `plan`
- `ranking`
- `score_vector`
- `tool_call_result`
- `validation_report`
- `trace_slice`
- `preview_sample`

## 6. Canonical Artifact Shape

TypedArtifact
- artifact_id: string
- artifact_type: string
- artifact_schema_version: string
- producer_ref: string
- payload: object
- metadata: object
- lineage_refs: list[string]
- trace_refs: list[string]
- validation_status: enum("unvalidated", "valid", "invalid", "partial")
- created_at: string

## 7. Input / Output Binding Rules

Every resource that produces or consumes a typed artifact should declare:

ArtifactIOContract
- accepted_input_types: list[ArtifactTypeRef]
- produced_output_types: list[ArtifactTypeRef]
- optional_output_types: list[ArtifactTypeRef]
- transform_requirements: list[TransformRequirement]

ArtifactTypeRef
- artifact_type: string
- schema_version: string
- compatibility_mode: enum("exact", "backward_compatible", "forward_compatible", "transform_required")

## 8. Transform Nodes

A transform node is required when:

- source artifact type mismatches consumer contract
- source schema version is incompatible
- payload normalization is required
- projection / summarization is needed for downstream use

Transform nodes must be explicit.
Implicit silent coercion is forbidden for canonical contracts.

## 9. Validation Rules

Typed artifact validation must check:

- declared type existence
- declared schema existence
- payload shape correctness
- required fields
- metadata sanity
- version compatibility
- transform requirement satisfaction

## 10. Version Rules

Artifact schemas must use explicit versions.

Minimum rule set:

- schema versions are immutable once published
- compatibility rules must be declared
- transform requirements must be explicit across incompatible versions
- downstream consumers may not silently assume latest

## 11. Trace and Replay Rules

Every canonical typed artifact should retain:

- producer reference
- parent lineage reference if derived
- trace reference
- validation result state

This is required for:
- replay
- diff
- bottleneck analysis
- post-run debugging
- verifier attribution

## 12. First Implementation Scope

The first implementation should support:

- artifact type registry
- schema version registry
- typed artifact envelope
- validation hook
- exact-match compatibility
- basic transform node contract
- trace linkage

## 13. Non-Goals for v0.1

Not required initially:

- arbitrary schema language support
- runtime self-evolving schema generation
- cross-project artifact marketplace semantics
- unrestricted version inference

## 14. Final Decision

The Typed Artifact Contract is the official stability layer for Nexa outputs.

It ensures that larger circuits do not collapse into:
"some output-looking dict somewhere"

Instead, they become:
"typed, versioned, traceable, validator-checkable artifacts"
