# Plugin Contract Family Index v1.1-b

## Recommended save path
`docs/specs/plugins/plugin_contract_family_index.md`

## 1. Purpose

This document is the official index for the plugin contract family in Nexa.

Its purpose is to:
- organize the full plugin contract set
- define the canonical reading order
- define the role of each contract
- clarify contract dependencies
- reduce ambiguity during implementation, review, debugging, and future AI-assisted work

This document does not replace the underlying contracts.
It is the routing and structure map for the plugin contract family.

## 2. Why This Index Exists

The plugin system in Nexa is no longer a single-document concern.

It now spans multiple contract layers:
- proposal and builder intake
- policy and namespace control
- runtime artifact identity
- publication and registry posture
- verification and test posture
- installation and loading
- runtime binding
- context I/O
- failure and recovery
- observability
- governance
- lifecycle state modeling

Without an explicit family index:
- reading order becomes inconsistent
- implementation may start from the wrong layer
- different documents may be misread as overlapping or contradictory
- future AI systems may lose the intended contract hierarchy

## 3. Core Classification Rule

The plugin contract family is organized into four major layers:
1. Builder / Proposal Layer
2. Artifact / Publication Layer
3. Runtime Operation Layer
4. Integration / Family Governance Layer

## 4. Current-State Legend

This family index distinguishes four status markers for implementation reading:

- `Current` = already strongly reflected in current code or document direction
- `Partial` = partially reflected but not yet fully unified
- `Target` = intended contract destination
- `Migration Required` = explicit bridge work is needed before direct implementation use

Unless otherwise noted, most of this plugin family should currently be read as `Target` or `Partial`, not as a claim of one-to-one code completeness.

## 5. Canonical Contract Set

### 4.1 Builder / Proposal Layer
1. Plugin Builder Spec Contract
2. Designer-to-Plugin-Builder Intake Contract
3. Plugin Namespace Policy Contract

### 4.2 Artifact / Publication Layer
4. Plugin Runtime Artifact / Manifest Contract
5. Plugin Registry Contract
6. Plugin Verification / Test Policy Contract

### 4.3 Runtime Operation Layer
7. Plugin Runtime Loading / Installation Contract
8. Plugin Runtime Execution Binding Contract
9. Plugin Context I/O Contract
10. Plugin Failure / Recovery Contract
11. Plugin Runtime Observability Contract
12. Plugin Runtime Governance Contract
13. Plugin Lifecycle State Machine Contract

### 4.4 Integration / Family Governance Layer
14. Plugin Classification & MCP Compatibility Contract
15. Plugin Contract Family Index

## 6. Canonical Reading Order

1. Plugin Builder Spec Contract
2. Designer-to-Plugin-Builder Intake Contract
3. Plugin Namespace Policy Contract
4. Plugin Runtime Artifact / Manifest Contract
5. Plugin Registry Contract
6. Plugin Verification / Test Policy Contract
7. Plugin Runtime Loading / Installation Contract
8. Plugin Runtime Execution Binding Contract
9. Plugin Context I/O Contract
10. Plugin Failure / Recovery Contract
11. Plugin Runtime Observability Contract
12. Plugin Runtime Governance Contract
13. Plugin Lifecycle State Machine Contract
14. Plugin Classification & MCP Compatibility Contract
15. Plugin Contract Family Index

## 7. Contract-by-Contract Question Map

- Plugin Builder Spec Contract: How is a plugin proposed, normalized, generated, validated, verified, and registered?
- Designer-to-Plugin-Builder Intake Contract: What may Designer AI send to the builder, and what remains proposal-space?
- Plugin Namespace Policy Contract: What may a plugin read or write, and how is approved namespace access enforced?
- Plugin Runtime Artifact / Manifest Contract: What is the canonical built plugin package, and what manifest must it carry?
- Plugin Registry Contract: How does a runtime artifact become registry-visible and discoverable?
- Plugin Verification / Test Policy Contract: What does it mean for a plugin to be verified?
- Plugin Runtime Loading / Installation Contract: How does a published or local artifact become installable, loaded, and activatable?
- Plugin Runtime Execution Binding Contract: How does an active plugin become a bound execution resource inside Node Runtime?
- Plugin Context I/O Contract: How does a bound plugin read from and write to Working Context?
- Plugin Failure / Recovery Contract: What happens when plugin execution fails or partially succeeds?
- Plugin Runtime Observability Contract: How do execution facts become events, metrics, trace slices, and artifact-linked evidence?
- Plugin Runtime Governance Contract: How does accumulated runtime evidence change operational posture?
- Plugin Lifecycle State Machine Contract: How do all plugin states fit together as one explicit lifecycle machine?
- Plugin Classification & MCP Compatibility Contract: Which plugin classes should or should not be primarily modeled as MCP-native, and how does approved classification bridge into artifact and loading truth?
- Plugin Contract Family Index: How should the whole family be read, navigated, and implemented?

## 8. Reading Order vs Real Dependency Structure

The family uses a canonical reading order,
but the real dependency structure is not purely linear.

Reading order exists to reduce conceptual confusion.
Dependency structure exists to show which contracts directly constrain others.

These two views must not be collapsed.

## 9. Conceptual Dependency Graph

The real dependency structure is better understood as a graph with strong direct links such as:

- Builder Spec -> Intake
- Builder Spec -> Namespace Policy
- Builder Spec -> Verification / Test
- Namespace Policy -> Runtime Artifact / Manifest
- Namespace Policy -> Runtime Loading / Installation
- Namespace Policy -> Runtime Execution Binding
- Namespace Policy -> Plugin Context I/O
- Runtime Artifact / Manifest -> Registry
- Runtime Artifact / Manifest -> Runtime Loading / Installation
- Verification / Test -> Runtime Loading / Installation
- Runtime Loading / Installation -> Runtime Execution Binding
- Runtime Execution Binding -> Plugin Context I/O
- Plugin Context I/O -> Failure / Recovery
- Failure / Recovery -> Runtime Observability
- Runtime Observability -> Runtime Governance
- Runtime Governance -> Lifecycle State Machine
- Designer-to-Plugin-Builder Intake -> Plugin Classification & MCP Compatibility
- Plugin Builder Spec -> Plugin Classification & MCP Compatibility
- Plugin Classification & MCP Compatibility -> Runtime Artifact / Manifest
- Plugin Classification & MCP Compatibility -> Runtime Loading / Installation
- Plugin Classification & MCP Compatibility -> Plugin Namespace Policy

This graph is not exhaustive,
but it is more accurate than a single linear chain.

## 10. Reading Order vs Implementation Order

Reading order follows conceptual clarity.
Implementation may batch nearby runtime concerns, but must still respect upstream invariants.

## 10. Layer Boundaries

- Builder / Proposal Layer: how plugins enter existence as governed candidates
- Artifact / Publication Layer: what the built plugin is and how it becomes visible
- Runtime Operation Layer: how the plugin becomes usable, executes, fails, emits evidence, and is governed
- Integration Layer: how the whole family is navigated and maintained

## 11. Canonical Implementation Guidance

A rational implementation approach should usually follow:
- Phase A: Builder and artifact formation
- Phase B: Publication and runtime intake
- Phase C: Runtime operation core
- Phase D: Runtime evidence and control
- Phase E: Family integration

## 12. Relationship to Current Plugin Contract Direction

This family index should be read as a cumulative refinement family, not as a claim that the current plugin direction started here.

In particular, the family must coexist explicitly with the existing plugin direction centered on:
- deterministic capability components
- Node Runtime
- Working Context
- PluginExecutor
- PRE / CORE / POST execution staging

This means the family index is authoritative for the new contract-family routing structure, but not for erasing prior plugin vocabulary by omission.

## 12. Authority Rules

The family index is authoritative only for:
- contract set membership
- reading order
- dependency overview
- role descriptions

If conflict appears, the specific contract governs its own subject matter.

## 13. Maintenance Rules

When the plugin contract family changes:
1. new contracts must be added here
2. removed or merged contracts must be updated here
3. reading order must be rechecked
4. dependency notes must be updated
5. implementation guidance may need revision

## 15. Explicitly Forbidden Patterns

- orphan contract creation
- reading-order ambiguity
- layer collapse
- hidden dependency assumptions
- family-index drift

## 17. Canonical Summary

- The plugin system is a contract family, not a single spec.
- The family has a canonical reading order and dependency map.
- Builder, artifact, runtime, and governance concerns must remain layered.
- The family index is necessary to keep the plugin spec set navigable, maintainable, and implementation-safe.

## 18. Final Statement

The plugin contract family in Nexa should not exist as a scattered pile of individually reasonable documents.

It should exist as one explicit, navigable, layered contract system whose reading order, dependencies, and roles remain clear over time.

That is the canonical meaning of Plugin Contract Family Index in Nexa.
