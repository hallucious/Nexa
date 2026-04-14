# BLUEPRINT

Version: 1.14.0

────────────────
Architecture Constitution
────────────────

Nexa follows an Execution Engine-based architecture.

The core design principles follow the Constitution defined in `docs/architecture/FOUNDATION_RULES.md`.

System invariants that MUST NOT be changed:

1. Nexa is not a workflow tool but an execution engine.
2. Node is the only execution unit.
3. Circuit does not perform execution and is responsible only for connections.
4. System-level execution is dependency-based. Fixed pipelines are prohibited.
5. Pre/core/post phases exist inside a Node, but they are the internal contract of a single node.
6. Artifacts are append-only immutable structures.
7. Deterministic execution must be maintained.
8. The plugin write scope is restricted to `plugin.<plugin_id>.*`.
9. The working context schema follows a fixed key structure.
10. Contract-driven architecture must be maintained.
11. Spec-version synchronization must be maintained.
12. Designer control-plane governance may tighten referential interpretation after repeated confirmation loops, and that policy escalation must remain explicit in session-state / precheck / preview surfaces.
13. Persisted governance carryover must clear once a later referential retry actually satisfies the stronger-anchor requirement; stale pending anchor requirements must not linger indefinitely across later cycles.
14. Once governance carryover has been cleared, its resolution may remain only as low-priority recent-resolution context for later referential follow-up, and any newly unresolved governance revision must supersede and remove that older resolution history.
15. Explicit scope redirect must archive older approval/revision thread continuity out of the active continuity store; redirected thread history may remain only as low-priority background context and must not continue constraining later mutations as if it were still the active thread.
16. If the user explicitly reopens an archived redirected scope, the restored active continuity must remain marked as reopened-from-archive during its active recent-history window rather than being silently flattened into ordinary recent continuity.
17. If a previously reopened older thread is later replaced by a newer active revision thread, the reopened-origin marker must stop governing active continuity and may remain only as short-lived low-priority replacement context.

Any implementation that violates these rules is considered a violation of the Nexa architecture.

---

## 0. Execution Philosophy (NEW)

Nexa treats execution as a portable, reproducible unit rather than a runtime-only process.

Execution is not defined by code alone, but by:

* Circuit definition
* Plugin environment
* Execution contract
* Deterministic runtime behavior

This enables:

* Reproducibility
* Portability
* Debuggability
* Environment isolation

---

## 1. Foundation Layer

The foundational design documents of this project are managed hierarchically by the following document:

* `docs/FOUNDATION_MAP.md`

When performing structure changes or contract changes, FOUNDATION_MAP must be referenced, and the status and SemVer of the affected documents must be checked.

---

## 2. Active Specifications

Currently active spec documents that are synchronized with the code.

Source-of-Truth: `docs/specs/_active_specs.yaml`

### 2.1 Foundation / Terminology

* `docs/specs/foundation/terminology.md`

### 2.2 Architecture Core

* `docs/specs/architecture/execution_model.md`
* `docs/specs/architecture/trace_model.md`
* `docs/specs/architecture/node_abstraction.md`
* `docs/specs/architecture/node_execution_contract.md`
* `docs/specs/architecture/circuit_contract.md`
* `docs/specs/architecture/universal_provider_architecture.md`
* `docs/specs/architecture/subcircuit_node_architecture.md`

### 2.3 Contracts

* `docs/specs/contracts/execution_environment_contract.md`
* `docs/specs/contracts/provider_contract.md`
* `docs/specs/contracts/plugin_contract.md`
* `docs/specs/contracts/prompt_contract.md`
* `docs/specs/contracts/plugin_registry_contract.md`
* `docs/specs/contracts/validation_engine_contract.md`
* `docs/specs/contracts/execution_config_canonicalization_contract.md`
* `docs/specs/contracts/execution_config_schema_contract.md`
* `docs/specs/contracts/context_key_schema_contract.md`
* `docs/specs/contracts/subcircuit_node_contract.md`

### 2.4 Policies

* `docs/specs/policies/validation_rule_catalog.md`
* `docs/specs/policies/validation_rule_lifecycle.md`

### 2.4.1 Storage / Savefile Extensions

* `docs/specs/storage/savefile_subcircuit_extension.md`

### 2.5 Indexes

* `docs/specs/indexes/spec_catalog.md`
* `docs/specs/indexes/spec_dependency_map.md`
* `docs/specs/subcircuit_node_spec_index.md`

### 2.5.1 Official Examples

* `docs/specs/examples/review_bundle_subcircuit_example.md`

### 2.5.2 Implementation Plans

* `docs/specs/implementation/subcircuit_node_implementation_batches.md`

### 2.6 ExecutionConfig

* `docs/specs/execution_config_prompt_binding_contract.md`
* `docs/specs/execution_config_registry_contract.md`

---

## 2.7 Supporting UI / I18n Reference Set

The following documents currently serve as **supporting UI-sector references**.
They are important for UI architecture continuity, but they are **not** yet part of the YAML-backed code-synchronized active spec core.

### 2.7.1 UI Architecture / Module References

* `docs/specs/ui/ui_architecture_package.md`
* `docs/specs/ui/ui_adapter_view_model_contract.md`
* `docs/specs/ui/graph_workspace_view_model_spec.md`
* `docs/specs/ui/inspector_panel_view_model_spec.md`
* `docs/specs/ui/validation_panel_view_model_spec.md`
* `docs/specs/ui/execution_panel_view_model_spec.md`
* `docs/specs/ui/designer_panel_view_model_spec.md`
* `docs/specs/ui/trace_timeline_viewer_view_model_spec.md`
* `docs/specs/ui/artifact_viewer_view_model_spec.md`
* `docs/specs/ui/storage_panel_view_model_spec.md`
* `docs/specs/ui/diff_viewer_view_model_spec.md`
* `docs/specs/ui/theme_layout_layer_spec.md`
* `docs/specs/ui/ui_state_ownership_and_persistence_spec.md`
* `docs/specs/ui/ui_section_schema_spec.md`
* `docs/specs/ui/ui_section_branch_rules_spec.md`
* `docs/specs/ui/ui_public_api_exposure_spec.md`
* `docs/specs/ui/ui_commit_boundary_stripping_spec.md`
* `docs/specs/ui/ui_typed_model_binding_spec.md`
* `docs/specs/ui/ui_workflow_collaboration_protocol.md`

### 2.7.2 UI Internationalization / Localization References

* `docs/specs/ui/ui_i18n_spec_index.md`
* `docs/specs/ui/ui_i18n_bundle_manifest.md`
* `docs/specs/ui/ui_multilingual_localization_architecture.md`
* `docs/specs/ui/ui_language_settings_contract.md`
* `docs/specs/ui/i18n_resource_schema_spec.md`
* `docs/specs/ui/ui_i18n_fallback_behavior_spec.md`
* `docs/specs/ui/localized_message_resolution_spec.md`
* `docs/specs/ui/validation_reason_code_localization_spec.md`
* `docs/specs/ui/ai_response_language_policy_spec.md`
* `docs/specs/ui/ui_i18n_persistence_boundary_spec.md`
* `docs/specs/ui/localization_test_strategy_spec.md`

Rule:

* These UI/i18n documents must respect engine-owned truth, approval truth, execution truth, and storage lifecycle truth.
* They must not be added to `docs/specs/_active_specs.yaml` until code and contract tests are synchronized with them.

---

## 3. ExecutionConfig Architecture

There is no Node type.

A Node is a single common execution container,
and behavioral diversity is expressed only through ExecutionConfig composition.

* Node = execution container
* Behavior = ExecutionConfig composition
* NodeSpec = ExecutionConfig reference
* ExecutionConfig identity = canonical hash

Execution layer:

Engine
→ GraphExecutionRuntime
→ NodeSpec
→ NodeSpecResolver
→ ExecutionConfigRegistry
→ ExecutionConfig Schema Validation
→ ExecutionConfig Hash
→ NodeExecutionRuntime

---
## 3.0 Current Project Position Snapshot

Current implementation baseline:

* authoritative implementation baseline commit: `ffc479d`
* authoritative verified baseline: `2285 passed, 14 skipped`
* the canonical macro roadmap still comes from `nexa_implementation_order_final_v2_2.md`
* the practical codebase state has now progressed through **Phase 7 return-use loop closure and Phase 8 inclusion/product-completeness closure** on top of the earlier Phase 4.5 server/product continuity foundation
* the repository now contains both the broad server-side continuity layer (workspace, onboarding, run, provider, artifact/trace, aggregate, user-scope, and setup-entry surfaces) and the product-facing return-use surfaces built on that continuity truth
* `src/server/` now contains the main continuity families plus the product-facing return-use families required for Phase 7: circuit library runtime, result history runtime, feedback runtime/store, HTTP route surface, framework binding, and FastAPI binding
* `src/server/database_foundation.py` remains the canonical persistence-family foundation for workspace registry, run history, onboarding state, managed provider bindings, provider probe events, artifact index, and trace event index
* continuity support stores now include provider binding, managed secret metadata, provider probe history, workspace registry, onboarding state, and the Phase 7 in-product feedback store
* the route/binding surface already exposes product/API continuity reads and writes for workspace, onboarding, provider operations, run launch/status/result/list, artifact detail, trace, recent activity, history summary, circuit library, result history, and feedback channel flows
* aggregate continuity projection is now joined by surfaced inclusion / product-completeness refinement so users can reenter through library, result history, onboarding continuity, feedback, and localized shell surfaces without relying on storage-internal literacy
* top-level project-truth documents must therefore be interpreted against the `ffc479d` codebase rather than the older `12577dc` Phase 7-only status world
* this practical server/product progress does **not** mean the macro productization sequence has been superseded: it means the repository has now practically closed the roadmap's Stage 3 and Stage 4 lines and should move its next official implementation focus to **Phase 9 (Stage 5 product expansion)** work

Interpretation rule:

* do not treat provider probe persistence as the next still-open main seam for this baseline
* do not treat local `.nex.ui` continuity and server continuity as the same thing
* do not skip the explicit proposal boundary:
  Intent -> Patch -> Precheck -> Preview -> Approval -> Commit
* sync authoritative truth first, then choose only a clearly justified next bounded seam

---
## 3.1 Current Runtime Convergence Snapshot

The current runtime line is intentionally concentrated into a smaller set of practical execution files.

### Prompt side

* `src.engine.node_execution_runtime.NodeExecutionRuntime` is the practical prompt execution caller
* prompt resolution is handled through `src.platform.prompt_registry.PromptRegistry` and PromptSpec loading
* No standalone legacy prompt package remains in the repository; the canonical runtime prompt path is the `src/platform/prompt_*` line.

### Provider side

* provider execution is routed through `src.platform.provider_executor.ProviderExecutor`
* provider lookup is handled through `src.platform.provider_registry.ProviderRegistry`
* provider result canonicalization is concentrated in the runtime path

### Plugin side

The plugin surface is currently split by role rather than duplicated legacy ownership:

* practical runtime execution side:
  * `src/engine/node_execution_runtime.py`
  * `src/platform/plugin_executor.py`
* `src/platform/plugin_result.py`
* runtime bridge loader for savefile entry references:
  * `src/platform/plugin_auto_loader.py`
* canonical versioned registry side:
  * `src/platform/plugin_version_registry.py`
* execution contract / safe execution side:
  * `src/platform/plugin.py`
* bundle/savefile compatibility side:
  * `src/engine/cli.py` (pure bounded compatibility wrapper for the legacy engine CLI surface)
  * `src/contracts/savefile_executor_aligned.py`

Current savefile plugin execution delegates entry-path execution to
`src/platform/plugin_executor.py`, so the savefile layer does not re-implement
callable wrapping or safe-execution adaptation.

Removed legacy ownership paths:

* `src/engine/plugin_loader.py`
* `src/platform/plugin_registry.py`

This means new runtime work MUST build from the converged files above rather than recreating the deleted legacy paths.

Legacy `.nex` compatibility runtime concentration:

* `.nex` execution compatibility is now split across canonical modules: `src/engine/cli.py` is a bounded compatibility shim, `src/cli/savefile_runtime.py` owns savefile/legacy execution dispatch, summary building, payload emission, and baseline-policy application, `src/engine/cli_policy_integration.py` owns policy integration primitives, and `src/circuit/runtime_adapter.py` owns legacy preparation and adaptation logic
* legacy `.nex` support is execution-only; reverse conversion / writer / roundtrip preservation are no longer part of the supported runtime surface
* deleted legacy contract leaves:
  * `src/contracts/nex_loader.py`
  * `src/contracts/nex_engine_adapter.py`
  * `src/contracts/nex_bundle_loader.py`
  * `src/contracts/nex_format.py`
  * `src/contracts/nex_serializer.py`
  * `src/contracts/nex_validator.py`


---

## 4. Savefile & Bundle System (NEW)

### 4.1 `.nex` Storage Family

`.nex` remains the primary Nexa storage family, but it is now role-aware.

The official storage-role split is:

* `meta.storage_role=working_save` -> Working Save
* `meta.storage_role=commit_snapshot` -> Commit Snapshot

Execution history does not live as a `.nex` role.
Execution history is represented by the Execution Record layer.

The official three-layer storage architecture is:

* Working Save
* Commit Snapshot
* Execution Record

The active lifecycle transition is:

Working Save
→ Commit Snapshot
→ Execution Record
→ Updated Working Save summary

This means Nexa storage now preserves three distinct truths:

* editable present-state truth -> Working Save
* approved structural truth -> Commit Snapshot
* realized run history truth -> Execution Record

`Working Save` remains always-saveable and may remain incomplete or invalid.
`Commit Snapshot` is approval-gated and must not be created from unresolved blocking state.
`Execution Record` is run-scoped and must always reference one approved `commit_id`.

Canonical storage semantics must be owned by storage/lifecycle APIs, not by CLI/export/replay path-local assembly.

Current storage-owned entry points implemented in code:

* `src/storage/nex_api.py`
  * `load_nex(...)`
  * `validate_working_save(...)`
  * `validate_commit_snapshot(...)`
* `src/storage/lifecycle_api.py`
  * shared serialized transition / execution-artifact component builders
* `src/storage/serialization.py`
  * role-aware write-path validation and canonicalization
* `src/storage/models/`
  * `WorkingSaveModel`
  * `CommitSnapshotModel`
  * `ExecutionRecordModel`
  * `LoadedNexArtifact`

Current official savefile CLI surface remains bounded:

* `nexa savefile new <output.nex>`
* `nexa savefile validate <file.nex>`
* `nexa savefile info <file.nex>`
* `nexa savefile template list`
* `nexa savefile set-name <file.nex> --name ...`
* `nexa savefile set-entry <file.nex> --entry ...`
* `nexa savefile set-description <file.nex> --description ...`

Boundary status:

* bounded savefile CLI editing remains intentionally limited
* broader structural editing is not yet a fully general CLI editing surface
* storage role semantics, lifecycle boundaries, and execution-artifact truth ordering are now storage-owned concerns
* CLI / export / replay must consume the same storage/lifecycle vocabulary rather than re-deriving semantics locally

---

### 4.2 Bundle (.nexb)

`.nexb` is a deployable execution unit.

It contains:

* `.nex` circuit file
* plugin directories
* plugin metadata (`plugin.json`)

Properties:

* self-contained execution unit
* environment reproducibility
* portable distribution

---

### 4.3 Execution Flow

CLI execution flow:

```
CLI
→ detect file extension
→ .nex → direct execution
→ .nexb → bundle extraction
→ plugin validation
→ engine execution
→ cleanup
```

---

### 4.4 Plugin Contract Enforcement

All plugins MUST:

* include `plugin.json`
* satisfy strict version matching
* comply with plugin contract spec

Validation is performed BEFORE execution.

---

## 4.5 Public Demo Baseline

The repository currently keeps one official demo path for public GitHub usage:

* `examples/real_ai_bug_autopsy_multinode/`

Other demo/example assets were intentionally removed to prevent deleted demo files from remaining as hidden test dependencies.

---

## 5. Regression Policy Architecture

`contracts/regression_reason_codes.py`  (single source of truth)
↓
`engine/execution_regression_detector.py`  (RegressionResult)
↓
`engine/execution_regression_policy.py`   (PolicyDecision: PASS/WARN/FAIL)
↓
formatter / CLI

Policy rules (default):

* HIGH severity regression → FAIL
* MEDIUM severity regression → WARN
* LOW severity / no regression → PASS

---

## 6. Universal Artifact Diff Architecture (NEW)

Nexa defines artifact comparison as a first-class architectural component.

All artifact comparison MUST follow a media-agnostic pipeline:

Artifact
→ Representation
→ ComparableUnit[]
→ Alignment
→ DiffResult
→ Formatter

### 6.1 Core Principle

- Raw artifact comparison is prohibited
- All comparison must operate on structured representations
- Comparison must be deterministic and reproducible

### 6.2 ComparableUnit Abstraction

ComparableUnit is the universal comparison unit across all media types.

Properties:

- unit_kind is extensible (section, scene, function, region, etc.)
- canonical_label enables cross-artifact alignment
- payload contains comparison-relevant data

This abstraction allows Nexa to support:
- text
- image
- video
- audio
- code
- structured data
- unknown future media

without modifying the core engine.

### 6.3 Layer Separation

The comparison system is strictly layered:

1. Extractor (Artifact → Representation)
2. Alignment (unit matching)
3. Comparison (unit-level diff)
4. Formatter (output only)

Formatter MUST NOT generate semantic meaning.

### 6.4 Architectural Constraint

The diff engine MUST remain media-agnostic.

Adding new media types MUST require ONLY:
- new extractor implementation

No modification to:
- alignment engine
- comparison engine
- formatter core

### 6.5 Relationship to Execution Engine

Artifact Diff operates as a downstream system of execution:

Execution Engine → Artifacts → Diff Engine

The diff engine does NOT influence execution semantics.

### 6.6 Representation Definition

Representation is a structured, deterministic transformation of an Artifact.

It is the ONLY valid input to the diff engine.

Properties:

- MUST be deterministic
- MUST be reproducible
- MUST be independent from formatter
- MUST consist of ComparableUnit[]

Structure:

Representation {
    representation_id: str
    artifact_type: str
    units: List[ComparableUnit]
    metadata: dict
}

---



* legacy `.nex` plugin validation is owned by `src/platform/external_loader.py`; CLI keeps only branching, savefile fallback, and policy/output handling


- Legacy engine CLI compatibility is now fully wrapper-oriented: `src/engine/cli.py` is the bounded engine compatibility shim, `src/cli/savefile_runtime.py` owns savefile/legacy execution dispatch, summary generation, payload emission, and baseline-policy wrapping, and `src/circuit/runtime_adapter.py` owns legacy preparation/adaptation logic.


- Execution record foundation implemented in code: contract, model, serialization, and working-save summary integration.


* Storage lifecycle linkage started: Working Save → Commit Snapshot creation and Execution Record → Working Save last-run summary update APIs


* Storage runtime linkage implemented in code: Commit Snapshot–anchored Execution Record creation and Working Save last-run update can now be driven from one lifecycle path


- repeat-cycle housekeeping semantics now rotate stale fresh-cycle markers and reduce them back into compact committed-summary notes after successful commit


- Current Phase 2 note: Designer post-commit continuity now includes bounded committed-summary retention rather than unbounded note accumulation.


- reference_resolution_policy: latest committed summary may auto-resolve generic last/previous references; second-latest and exact commit-id references are allowed when explicit; non-latest older references without a precise anchor must remain explicit ambiguities.

* Designer-bounded mixed referential reason catalog now lives in `src/designer/reason_codes.py`; these codes are reused across normalization / patch / precheck / preview and are intentionally not promoted to the shared global reason-code framework yet

* approval-resolution revision flow now preserves Designer-bounded mixed referential reason codes in `revision_state.retry_reason` and `notes.last_revision_reason_code` instead of collapsing back to a generic approval revision marker

* mixed referential reason retention now follows an explicit lifecycle boundary: active notes only remain live during the current revision cycle, commit cleanup archives them into history-only notes, and fresh unrelated cycles clear transient mixed-reason markers before new interpretation begins
* governance-tier surfacing is now applicability-aware: non-referential requests should not inherit irrelevant referential friction, and already-anchored requests should downgrade from confirmation-style governance to warning-style governance while the elevated tier remains active
* governance policy is now reused across approval/revision safety boundaries: governance confirmation findings generate richer approval decision guidance, and governance-triggered revision requests persist explicit anchor guidance back into session-state continuity


- safe non-referential cycles now contribute explicit decay progress; after enough consecutive safe cycles, elevated/strict governance can deescalate one tier even without a new referential anchor event
- governance now also records an explicit ambiguity-pressure score/band; this gives the control plane a calibration-friendly numeric trace for repeated confirmation pressure, anchored relief, and safe-cycle decay
- ambiguity-pressure summaries are now expected to remain reusable across precheck/preview/approval surfaces so governance intensity does not disappear into notes-only state

* revision-request continuity now persists structured governance guidance, including anchor requirement mode, pressure summary/score/band, and next-safe-action hints so the next cycle inherits pressure-aware anchor guidance instead of only a generic note
* persisted governance carryover is now request-applicability-aware at rebuilt session-card time: non-referential follow-up requests should not keep surfacing stale pending-anchor risk, and already-anchored referential retries should surface carryover as warning-level context rather than unresolved-governance pressure

* approval-boundary continuation now keeps a compact recent revision history (bounded) so rebuilt session cards and the normalizer can recognize longer multi-step revision threads and preserve the latest clarified direction unless the user explicitly redirects scope

* compact recent approval/revision continuity is now redirect-aware: if a new mutation request explicitly redirects scope away from the latest clarified interpretation, rebuilt session cards and normalization retain the old thread only as background history instead of surfacing it as active continuity pressure; if the user later explicitly returns to that older scope, the archived thread is restored as active continuity again
* active compact approval/revision continuity history now also expires after a short nearby follow-up window unless a new revision thread reinforces it, so stale multi-step continuity does not remain active indefinitely


- Redirected recent revision threads are archived out of active continuity using `approval_revision_redirect_archived_*` notes and are cleared when a new active revision thread forms.
- Explicit reopen of the archived older scope restores that redirected thread into active continuity and should surface as reopened-thread continuity rather than ordinary recent-history reuse.
- If that reopened older thread is later replaced by a newer active revision thread, rebuilt session cards and normalization should preserve the newer thread as active continuity and treat the older reopened origin only as short-lived replacement history.
