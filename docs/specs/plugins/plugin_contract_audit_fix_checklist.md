# Plugin Contract Audit Fix Checklist v1.0

## Recommended save path
`docs/specs/plugins/plugin_contract_audit_fix_checklist.md`

## 1. Purpose

This document defines the immediate fix checklist for the current Plugin Contract Family
after reviewing the external audit report against the current Nexa codebase.

Its purpose is to:

- separate valid audit findings from overstated findings
- define the highest-priority corrections
- preserve the current plugin contract family direction
- close the translation gap between the new contract family and the existing codebase

This document does not replace the plugin contract family.
It defines the corrective patch order required before implementation-grade use.

## 2. Core Decision

The plugin contract family direction remains valid.

The main problem is not that the new documents chose the wrong architecture.
The main problem is that several documents do not yet explain clearly enough how the new contract family relates to the current Nexa codebase.

In short:

- keep the contract family direction
- fix naming collisions
- remove forbidden terminology
- add implementation-context bridge sections
- explicitly align with current runtime/plugin structures

## 3. Patch Priority Rule

Priority must be determined by this rule:

Fix first the items that can create implementation ambiguity,
naming collision, or architecture-rule misunderstanding.

Therefore the priority order is:

1. terminology collisions and forbidden terms
2. current-code alignment gaps
3. missing bridge explanations
4. document-governance synchronization
5. lower-severity structural refinements

## 4. P0 — Must Fix Immediately

### 4.1 Remove forbidden `pipeline` terminology from Plugin Builder Spec Contract

**Problem**
The current Plugin Builder Spec Contract uses the word `pipeline` in several places.
This is risky because Nexa architecture rules explicitly discourage pipeline-style runtime framing.

**Required action**
Replace all uses of:
- `pipeline`
- `multi-stage pipeline`
- `pipeline owner`

with terms such as:
- `stage sequence`
- `multi-stage process`
- `stage orchestrator`
- `governed stage sequence`
- `stage-sequence owner`

**Target document**
- `docs/specs/plugins/plugin_builder_spec_contract.md`

**Acceptance condition**
No remaining normative use of `pipeline` appears in the plugin contract family
where it could be interpreted as execution-model vocabulary.

### 4.2 Resolve `PluginManifest` naming collision

**Problem**
The current codebase already uses `PluginManifest` in existing platform/plugin code.
The new plugin contract family reused the same name for a substantially different object shape.

**Required action**
Rename the manifest object defined in the runtime artifact / manifest contract.

**Recommended replacement**
- `PluginArtifactManifest`

Alternative acceptable name:
- `PluginBuilderManifest`

**Preferred direction**
Use `PluginArtifactManifest` because it most clearly communicates:
- artifact-level role
- distinction from builder request
- distinction from existing runtime/plugin discovery manifests

**Target document**
- `docs/specs/plugins/plugin_runtime_artifact_manifest_contract.md`

**Required follow-up**
Add an explicit section explaining the relationship between:
- existing `PluginManifest` names in code
- the new contract-level artifact manifest concept
- future migration / coexistence expectations

**Acceptance condition**
The contract family no longer introduces a third conflicting `PluginManifest` meaning.

### 4.3 Explicitly separate `plugin_category` from current `plugin_type`

**Problem**
The new documents use `plugin_category` for one purpose,
while current code uses `plugin_type` for another purpose.
If this is not made explicit, future implementation may incorrectly merge them.

**Required action**
Add a normative distinction section stating that:

- `plugin_category` is a builder/spec/purpose classification axis
- `plugin_type` is an existing runtime/platform/plugin-role classification axis
- the two fields are not synonyms
- one must not silently replace the other

**Target documents**
- `docs/specs/plugins/plugin_builder_spec_contract.md`
- `docs/specs/plugins/plugin_runtime_artifact_manifest_contract.md`
- `docs/specs/plugins/plugin_registry_contract.md`

**Acceptance condition**
A future implementer can clearly tell that:
- category answers “what kind of plugin purpose is this?”
- type answers “what runtime/plugin-role class is this in current code?”

### 4.4 Add PRE / CORE / POST stage compatibility bridge

**Problem**
The current codebase and existing plugin direction still use stage vocabulary such as PRE / CORE / POST.
The new plugin contract family does not currently explain how its model maps to that reality.

**Required action**
Add compatibility text stating that the new plugin contract family:
- does not erase the existing PRE / CORE / POST execution-stage model
- sits above or beside that model depending on document scope
- must be interpreted as contract-family expansion, not replacement by omission

**Minimum mapping requirement**
The documents do not need to fully redesign the stage model now,
but they must explain whether a given contract concerns:
- build-time lifecycle
- publication-time lifecycle
- runtime acceptance
- runtime execution
- runtime governance

and how that coexists with PRE / CORE / POST execution staging.

**Target documents**
- `docs/specs/plugins/plugin_builder_spec_contract.md`
- `docs/specs/plugins/plugin_runtime_execution_binding_contract.md`
- `docs/specs/plugins/plugin_context_io_contract.md`
- `docs/specs/plugins/plugin_failure_recovery_contract.md`
- `docs/specs/plugins/plugin_runtime_observability_contract.md`

**Acceptance condition**
A reader of the new family cannot reasonably conclude that PRE / CORE / POST has been implicitly deleted.

### 4.5 Add explicit current-code implementation-context sections

**Problem**
The new contract family defines a strong target architecture,
but it often does not explain how that target relates to current loader/discovery/executor code.

**Required action**
Add an `Implementation Context` or `Current Codebase Alignment` section where appropriate.

The section should explicitly state one of the following:
- this contract describes a target structure not yet fully present in code
- this contract extends an existing subsystem
- this contract coexists with existing thin wrappers / transitional layers
- this contract requires migration work before direct implementation

**Priority target documents**
- `docs/specs/plugins/plugin_builder_spec_contract.md`
- `docs/specs/plugins/plugin_runtime_artifact_manifest_contract.md`
- `docs/specs/plugins/plugin_registry_contract.md`
- `docs/specs/plugins/plugin_runtime_execution_binding_contract.md`
- `docs/specs/plugins/plugin_contract_family_index.md`

**Minimum content**
Each such section should mention the relevant current code families such as:
- discovery
- auto-loading
- current executor layer
- platform/plugin registry structures
- existing plugin contract vocabulary

**Acceptance condition**
A future implementer can see where the document is:
- already aligned
- partially aligned
- forward-looking

without guessing.

## 5. P1 — Strongly Recommended Before Broader Use

### 5.1 Refine the family dependency map

**Problem**
The current family index presents the dependency structure too linearly.
In reality the dependency shape is closer to a graph.

**Required action**
Update the family index to distinguish:
- reading order
- conceptual dependency order
- implementation batching opportunities

**Target document**
- `docs/specs/plugins/plugin_contract_family_index.md`

**Acceptance condition**
A future reader does not confuse:
- “read this first”
with
- “this is the only upstream dependency”

### 5.2 Add explicit coexistence language for existing plugin contract v1.1.0

**Problem**
The current codebase already has a plugin contract direction centered on:
- deterministic capability component
- Node Runtime
- Working Context
- PluginExecutor
- PRE / CORE / POST stage structure

The new family must present itself as an extension / refinement family,
not as if it were the first plugin contract ever written.

**Required action**
Add explicit relationship text to the new family index and selected runtime documents.

**Target documents**
- `docs/specs/plugins/plugin_contract_family_index.md`
- `docs/specs/plugins/plugin_runtime_execution_binding_contract.md`
- `docs/specs/plugins/plugin_context_io_contract.md`
- `docs/specs/plugins/plugin_runtime_observability_contract.md`

**Acceptance condition**
The family reads as:
- cumulative refinement
not
- silent replacement by omission

### 5.3 Add a “current state vs target state” legend

**Problem**
Some documents describe target-state contracts,
but not all readers will know whether the shape already exists in code.

**Required action**
Add one short legend, either family-wide or per document, using labels such as:
- `Current`
- `Partial`
- `Target`
- `Migration Required`

**Best placement**
- family index
- builder spec
- runtime artifact / manifest
- runtime execution binding

**Acceptance condition**
Implementation planning can distinguish immediate coding work from future contract targets.

## 6. P2 — Governance / Documentation System Sync

### 6.1 Plan spec-version registration

**Problem**
The new documents should eventually participate in spec-version synchronization.

**Required action**
Prepare the follow-up plan to register the plugin contract family in the spec-version sync system when the document set is stabilized.

**Target areas**
- spec version registry / version map documents
- later code sync work

**Acceptance condition**
There is no ambiguity about whether these plugin contracts are intended to become governed specs.

### 6.2 Add the family to document maps / indexes

**Problem**
A contract family that exists without appearing in higher-level document maps will drift.

**Required action**
Plan the update of higher-level maps/indexes such as:
- plugin family references
- foundation/spec indexes
- document-set navigation docs

**Acceptance condition**
The plugin family is no longer structurally orphaned.

## 7. Findings the Audit Overstated

The audit was broadly useful,
but the following must be interpreted carefully.

### 7.1 Raw issue count is not the real severity model
A raw count such as “16 issues” is not the best interpretation.
Several findings are multiple expressions of the same deeper gap:
the bridge between the new contract family and the current codebase.

### 7.2 The contract family direction itself is not invalid
The audit itself recognized that the overall direction is structurally sound.
The core problem is not wrong architecture.
The core problem is missing translation and coexistence context.

### 7.3 Not every omission is a P0 defect
Some omissions are immediate implementation blockers.
Others are documentation-governance follow-ups.
These must not be mixed together.

## 8. Recommended Patch Execution Order

The practical patch order should be:

### Batch 1 — collision / terminology fixes
- remove `pipeline`
- rename `PluginManifest`
- distinguish `plugin_category` vs `plugin_type`

### Batch 2 — runtime alignment bridge
- add PRE / CORE / POST compatibility text
- add current-code implementation-context sections

### Batch 3 — family-structure refinements
- refine dependency graph language
- add coexistence language with current plugin contract v1.1.0
- add current-vs-target markers

### Batch 4 — doc governance sync
- spec-version sync plan
- higher-level index / map inclusion

## 9. Completion Criteria

This checklist is complete only when all of the following are true:

1. No forbidden `pipeline` language remains in normative plugin-family text.
2. The artifact manifest object no longer collides with existing `PluginManifest` names.
3. `plugin_category` and `plugin_type` are explicitly separated.
4. PRE / CORE / POST compatibility is explicitly acknowledged where needed.
5. Current-code alignment sections exist in the highest-risk documents.
6. The family index no longer overstates a linear dependency model.
7. The new contract family reads as an extension/refinement of the current plugin direction, not an accidental replacement.
8. A governance-sync follow-up plan exists for later document-system integration.

## 10. Final Statement

The plugin contract family does not need to be replaced.

It needs to be translated more carefully into Nexa’s existing code and document reality.

That is the correct meaning of the current audit result.
