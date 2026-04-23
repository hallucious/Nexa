# Plugin Builder Full Implementation Plan v1.0

## Recommended save path
`docs/implementation/plugins/plugin_builder_full_implementation_plan.md`

## 1. Purpose

This document defines the full implementation plan for the Nexa Plugin Builder system.

It is written so that another AI can use this document as the primary execution blueprint for implementing the Plugin Builder contract family end to end.

The goal is not to restate the specification documents in prose only.
The goal is to translate the specification family into a concrete build plan that answers all of the following:

- what to implement first
- what code to create or modify
- how to map the current repository to the target contract family
- what runtime and registry objects must exist
- what state transitions are legal
- what tests must be written
- what is considered done
- what must not be changed

This document assumes the uploaded plugin spec set is the authoritative target contract family and that the current repository baseline is the latest available code baseline at the time of planning.

---

## 2. Authoritative inputs

This plan is derived from the uploaded plugin specification family and current repository code state.

### 2.1 Primary authoritative specification set

The implementation target is the full plugin contract family:

1. `docs/specs/plugins/plugin_builder_spec_contract.md`
2. `docs/specs/plugins/designer_to_plugin_builder_intake_contract.md`
3. `docs/specs/plugins/plugin_namespace_policy_contract.md`
4. `docs/specs/plugins/plugin_runtime_artifact_manifest_contract.md`
5. `docs/specs/plugins/plugin_registry_contract.md`
6. `docs/specs/plugins/plugin_verification_test_policy_contract.md`
7. `docs/specs/plugins/plugin_runtime_loading_installation_contract.md`
8. `docs/specs/plugins/plugin_runtime_execution_binding_contract.md`
9. `docs/specs/plugins/plugin_context_io_contract.md`
10. `docs/specs/plugins/plugin_failure_recovery_contract.md`
11. `docs/specs/plugins/plugin_runtime_observability_contract.md`
12. `docs/specs/plugins/plugin_runtime_governance_contract.md`
13. `docs/specs/plugins/plugin_lifecycle_state_machine_contract.md`
14. `docs/specs/plugins/plugin_classification_mcp_compatibility_contract.md`
15. `docs/specs/plugins/plugin_contract_family_index.md`

### 2.2 Current repository alignment baseline

Current repository code already contains partial plugin families and must not be ignored.
The implementation must treat current code as migration-required, not as blank slate.

Existing relevant files already present:

- `src/platform/plugin.py`
- `src/platform/plugin_contract.py`
- `src/platform/plugin_definition.py`
- `src/platform/plugin_auto_loader.py`
- `src/platform/plugin_discovery.py`
- `src/platform/plugin_executor.py`
- `src/platform/plugin_result.py`
- `src/platform/plugin_version_registry.py`
- `src/engine/plugin_registry_fingerprint.py`
- `src/server/public_plugin_models.py`
- `src/server/public_plugin_runtime.py`
- multiple plugin-related tests under `tests/`

### 2.3 Planning rule

Implementation must satisfy the uploaded plugin contract family without breaking existing plugin/runtime tests unless the test must be intentionally superseded by a clearly justified migration.

---

## 3. Core decision

The Plugin Builder is not a code generator helper.
It is the official conversion boundary between proposal-space and trusted plugin-space.

That means the implementation must realize one coherent system with the following layers:

1. **Proposal / Intake layer**
2. **Builder orchestration layer**
3. **Validation / Verification layer**
4. **Artifact / Manifest layer**
5. **Registry publication layer**
6. **Runtime installation / loading / binding layer**
7. **Context I/O / execution / failure / observability layer**
8. **Governance / lifecycle / classification layer**

Anything less than this is not a full implementation of the uploaded specs.

---

## 4. Non-negotiable invariants

These are mandatory implementation invariants.
Do not violate them for convenience.

### 4.1 Node remains the sole execution unit
Plugins are capability resources inside node runtime execution.
A plugin must not become a new top-level execution unit.

### 4.2 Proposal-space and trusted plugin-space must remain distinct
Designer AI may propose plugin creation and builder drafts.
Designer AI must not directly install, trust, or publish plugins.

### 4.3 Registration is explicit
Build success does not imply registration.
Registration requires an explicit request and a permitted target scope.

### 4.4 Runtime loading is explicit
Registry publication does not imply installation.
Installation does not imply activation.
Activation does not imply bound execution.

### 4.5 Namespace policy must be explicit and allow-list based
Requested access and approved access must be separate objects.
Runtime must enforce approved policy; it must not trust self-declared plugin behavior.

### 4.6 Working Context remains the canonical I/O boundary
Plugin execution must read and write through explicit Working Context declarations.
No arbitrary runtime memory exposure is allowed.

### 4.7 Observability is engine truth
Events, metrics, failures, recoveries, and outcomes must be produced as structured runtime truth.
UI may render them but must not fabricate them.

### 4.8 Governance and lifecycle are explicit
Plugin posture changes such as restrict/suspend/quarantine/remove must be based on explicit evidence and explicit transitions.

### 4.9 MCP compatibility must not replace internal runtime truth
MCP is important, but internal runtime representation remains Nexa-native.
Classification and adapters must preserve this boundary.

### 4.10 Backward compatibility is a migration problem, not a reason to ignore target contracts
Current `src/platform/*` code should be bridged, not blindly deleted.

---

## 5. Current repository assessment

The current repository already has a minimal plugin substrate, but it does not yet implement the full builder contract family.

### 5.1 What already exists

The following concepts already exist in some form:

- plugin callable execution
- plugin manifest/version registry
- plugin discovery and auto-loading
- plugin executor routing
- plugin result normalization
- plugin registry fingerprinting
- some server/plugin catalog surface
- many contract tests around legacy plugin behavior

### 5.2 What is still missing relative to the target contract family

The following major pieces are still missing or too thin:

- unified builder request/result orchestration
- Designer-to-builder intake object family
- explicit normalized builder spec family
- explicit namespace request vs approved namespace policy split
- canonical runtime artifact + manifest family
- explicit registry entry family with policy/verification posture
- explicit installation state object
- explicit bound runtime object
- explicit plugin execution instance model
- explicit context input/output objects
- explicit failure state + recovery state objects
- explicit event/metric/trace slice family
- explicit runtime governance posture + decisions
- explicit lifecycle state machine object + transitions
- explicit plugin classification / MCP compatibility record

### 5.3 Practical migration conclusion

Do **not** attempt a giant in-place rewrite of `src/platform` first.
Instead:

- add the new contract family in a new implementation package
- bridge the existing platform package into it
- keep old tests green while adding new contract tests
- only later decide whether to converge old files into the new package

---

## 6. Target implementation shape

The cleanest implementation is a new `src/plugins/` package with bridges back to `src/platform/`.
This avoids contaminating old thin runtime code with every new contract at once.

### 6.1 Required package layout

Create the following package structure.

```text
src/plugins/
  __init__.py

  contracts/
    __init__.py
    builder_types.py
    intake_types.py
    namespace_types.py
    artifact_types.py
    registry_types.py
    verification_types.py
    installation_types.py
    binding_types.py
    context_io_types.py
    failure_types.py
    observability_types.py
    governance_types.py
    lifecycle_types.py
    classification_types.py
    common_enums.py
    serialization.py

  builder/
    __init__.py
    service.py
    modes.py
    intake_gate.py
    normalize.py
    classification.py
    template_resolver.py
    generator.py
    validator.py
    verifier.py
    registrar.py
    result_emitter.py
    storage.py
    findings.py

  registry/
    __init__.py
    catalog.py
    persistence.py
    search.py
    fingerprint.py

  runtime/
    __init__.py
    installation.py
    loader.py
    binding.py
    context_io.py
    execution.py
    failure_recovery.py
    observability.py
    governance.py
    lifecycle.py
    compatibility.py

  adapters/
    __init__.py
    legacy_platform_bridge.py
    legacy_registry_bridge.py
    server_bridge.py
    mcp_bridge.py
```

### 6.2 Existing files to modify, not replace immediately

Modify or bridge the following current files:

- `src/platform/plugin_auto_loader.py`
- `src/platform/plugin_executor.py`
- `src/platform/plugin_version_registry.py`
- `src/platform/plugin_definition.py`
- `src/platform/plugin_result.py`
- `src/platform/plugin_discovery.py`
- `src/engine/plugin_registry_fingerprint.py`
- `src/server/public_plugin_models.py`
- `src/server/public_plugin_runtime.py`

### 6.3 Optional but recommended new server files

Add:

```text
src/server/plugin_builder_models.py
src/server/plugin_builder_runtime.py
src/server/plugin_builder_routes.py
```

These should be thin server/public-facing surfaces around the builder service.

---

## 7. Canonical object model to implement

This section is normative for implementation.
The names below must exist in code as dataclasses or frozen dataclasses plus JSON serialization helpers.

Use Python dataclasses for first implementation, not Pydantic.
Reason:
- current repository already leans on dataclasses
- lower dependency risk
- easier compatibility with current tests
- enough for contract-preserving internal domain objects

### 7.1 Builder layer objects

#### PluginBuilderRequest

Fields:
- `request_id: str`
- `mode: str`
- `source_type: str`
- `builder_spec: PluginBuilderSpec | None`
- `existing_candidate_ref: str | None`
- `existing_registry_ref: str | None`
- `caller_context: BuilderCallerContext`
- `governance_context: BuilderGovernanceContext`
- `build_options: BuilderBuildOptions`
- `registration_request: RegistrationRequest | None`

#### PluginBuilderSpec

Fields:
- `spec_version: str`
- `plugin_purpose: str`
- `plugin_name_hint: str | None`
- `plugin_category: str`
- `capability_summary: str`
- `input_contract: PluginInputContract`
- `output_contract: PluginOutputContract`
- `side_effect_profile: SideEffectProfile`
- `namespace_policy: NamespacePolicyRequest`
- `runtime_constraints: RuntimeConstraintRequest`
- `dependency_requirements: DependencyRequirementSet`
- `template_preference: TemplatePreference`
- `safety_constraints: SafetyConstraintSet`
- `verification_requirements: VerificationRequirementSet`
- `registration_intent: RegistrationIntent`
- `classification_request: ClassificationRequest | None`
- `notes: str | None`

#### BuilderCallerContext

Fields:
- `caller_type`
- `caller_ref`
- `workspace_ref`
- `savefile_ref`
- `proposal_ref`
- `user_ref`

#### BuilderGovernanceContext

Fields:
- `approval_required`
- `human_review_required`
- `allowed_registration_scope`
- `risk_tier`
- `policy_profile`

#### BuilderBuildOptions

Fields:
- `generate_tests`
- `strict_validation`
- `strict_verification`
- `prefer_templates`
- `allow_partial_preview_defaults`
- `fail_on_warning`
- `include_scaffold_comments`
- `package_candidate`

#### RegistrationRequest

Fields:
- `requested`
- `target_registry_scope`
- `publish_label`
- `install_after_register`
- `activation_request`

#### PluginBuilderResult

Fields:
- `build_id`
- `request_id`
- `final_status`
- `normalized_spec`
- `generated_candidate_ref`
- `generated_files`
- `validation_report`
- `verification_report`
- `registry_record`
- `stage_reports`
- `blocking_findings`
- `warning_findings`
- `explanation`
- `recommended_next_action`

#### BuilderFinding

Fields:
- `finding_id`
- `severity`
- `stage`
- `code`
- `message`
- `target_ref`
- `remediation_hint`

### 7.2 Intake layer objects

#### DesignerPluginBuildProposal

Fields:
- `proposal_id`
- `proposal_version`
- `proposal_status`
- `originating_request_text`
- `designer_session_ref`
- `source_context`
- `requested_builder_mode`
- `plugin_builder_spec_draft`
- `ambiguity_report`
- `risk_report`
- `clarification_questions`
- `explanation`
- `recommended_next_action`

#### DesignerPluginSourceContext

Fields:
- `source_type`
- `workspace_ref`
- `savefile_ref`
- `circuit_ref`
- `node_ref`
- `existing_plugin_ref`
- `target_usage_summary`

#### PluginBuilderSpecDraft

Fields:
- `draft_version`
- `plugin_purpose`
- `plugin_name_hint`
- `plugin_category`
- `capability_summary`
- `intended_user_value`
- `expected_usage_context`
- `input_contract_draft`
- `output_contract_draft`
- `side_effect_profile_draft`
- `namespace_policy_request_draft`
- `runtime_constraint_request_draft`
- `dependency_requirement_draft`
- `template_preference_draft`
- `safety_constraint_draft`
- `verification_requirement_draft`
- `registration_intent_draft`
- `classification_request_draft`
- `unresolved_fields`
- `assumptions`
- `notes`

### 7.3 Namespace policy objects

#### RequestedNamespacePolicy

Fields:
- `requested_read_scopes`
- `requested_write_scopes`
- `requested_external_read_targets`
- `requested_external_write_targets`
- `policy_sensitivity`
- `rationale`
- `unresolved_questions`

#### NamespaceScopeRequest

Fields:
- `namespace_family`
- `scope_mode`
- `field_paths`
- `reason`

#### ApprovedNamespacePolicy

Fields:
- `policy_id`
- `read_scopes`
- `write_scopes`
- `external_read_targets`
- `external_write_targets`
- `denied_scopes`
- `enforcement_mode`
- `rationale_summary`
- `issued_by_stage`
- `policy_version`

#### RuntimeNamespaceEnforcementPolicy

Fields:
- `approved_policy_ref`
- `read_filter_mode`
- `write_filter_mode`
- `violation_mode`
- `trace_violations`

### 7.4 Artifact / manifest objects

#### PluginRuntimeArtifact

Fields:
- `artifact_id`
- `artifact_version`
- `build_ref`
- `manifest`
- `package_layout`
- `integrity`
- `provenance`

#### PluginPackageLayout

Fields:
- `entrypoint_module`
- `entrypoint_symbol`
- `source_files`
- `support_files`
- `test_files`
- `manifest_path`
- `packaging_format`

#### PluginArtifactManifest

Implement at minimum the fields named in the spec:
- `manifest_version`
- `plugin_id`
- `plugin_name`
- `plugin_display_name`
- `plugin_category`
- `plugin_type`
- `plugin_summary`
- `plugin_description`
- `artifact_version`
- `builder_spec_version`
- `runtime_contract_version`
- `entrypoint`
- `input_contract_summary`
- `output_contract_summary`
- `approved_namespace_policy_ref`
- `side_effect_summary`
- `dependency_summary`
- `verification_summary`
- `compatibility`
- `registry_readiness`
- `classification_summary`
- `manifest_notes`

Implementation rule:
The manifest object must be its own dataclass and must serialize independently from the outer artifact.

### 7.5 Registry objects

#### PluginRegistryEntry

Fields:
- `registry_entry_id`
- `plugin_id`
- `artifact_ref`
- `manifest_ref`
- `registry_version`
- `publication_status`
- `publication_scope`
- `visibility_metadata`
- `registry_summary`
- `policy_posture`
- `verification_posture`
- `provenance_summary`
- `governance_metadata`
- `timestamps`

### 7.6 Verification objects

#### PluginVerificationRequirements

Fields:
- `required_profile`
- `require_static_load_check`
- `require_smoke_execution`
- `require_io_contract_check`
- `require_template_integrity_check`
- `require_policy_alignment_check`
- `require_behavioral_test`
- `require_negative_scope_test`
- `additional_requirements`

#### PluginVerificationEvidence

Fields:
- `verification_run_id`
- `artifact_ref`
- `executed_profile`
- `executed_checks`
- `started_at`
- `completed_at`
- `overall_result`
- `notes`

#### PluginVerificationPosture

Fields:
- `verification_status`
- `verification_profile`
- `passed_check_count`
- `failed_check_count`
- `skipped_check_count`
- `blocking_failures_present`
- `posture_notes`

### 7.7 Installation / binding objects

#### PluginInstallationState

Fields:
- `installation_id`
- `plugin_id`
- `artifact_ref`
- `manifest_ref`
- `target_runtime_ref`
- `installation_scope`
- `install_status`
- `load_status`
- `activation_status`
- `installed_at`
- `last_loaded_at`
- `last_activated_at`
- `notes`

#### BoundPluginRuntime

Fields:
- `binding_id`
- `plugin_id`
- `artifact_ref`
- `manifest_ref`
- `installation_ref`
- `target_runtime_ref`
- `execution_stage`
- `executor_ref`
- `bound_policy_ref`
- `working_context_contract_ref`
- `read_declarations`
- `write_declarations`
- `external_target_bindings`
- `runtime_constraints`
- `activation_status`
- `notes`

#### PluginExecutionInstance

Fields:
- `execution_instance_id`
- `binding_ref`
- `node_execution_ref`
- `run_ref`
- `status`
- `started_at`
- `completed_at`
- `input_context_refs`
- `output_context_refs`
- `artifact_refs`
- `trace_event_refs`
- `failure_code`

### 7.8 Context I/O objects

#### PluginContextInput

Fields:
- `input_id`
- `execution_instance_ref`
- `plugin_id`
- `input_bindings`
- `normalized_payload`
- `extracted_context_refs`
- `extracted_at`
- `notes`

#### PluginContextOutput

Fields:
- `output_id`
- `execution_instance_ref`
- `plugin_id`
- `output_mode`
- `emitted_context_refs`
- `partial_output_present`
- `final_output_present`
- `artifact_refs`
- `emitted_at`
- `notes`

Implementation rule:
If exact field names of nested binding/result classes are ambiguous, derive them from the contract family and keep names consistent across builder, runtime, and tests.

### 7.9 Failure / recovery objects

#### PluginFailureState

Fields:
- `failure_state_id`
- `execution_instance_ref`
- `binding_ref`
- `plugin_id`
- `failure_category`
- `retryability`
- `severity`
- `failure_code`
- `failure_message`
- `partial_output_present`
- `artifact_partial_present`
- `context_partial_present`
- `escalation_required`
- `notes`

#### PluginRecoveryState

Fields:
- `recovery_state_id`
- `failure_state_ref`
- `recovery_policy_ref`
- `recovery_action`
- `recovery_attempt_count`
- `recovery_status`
- `final_outcome_ref`
- `notes`

### 7.10 Observability objects

#### PluginRuntimeEvent

Fields:
- `event_id`
- `execution_instance_ref`
- `binding_ref`
- `node_execution_ref`
- `run_ref`
- `event_type`
- `timestamp`
- `severity`
- `message`
- `related_context_keys`
- `related_artifact_refs`
- `related_failure_ref`
- `related_recovery_ref`
- `details`

#### PluginRuntimeMetric

Fields:
- `metric_id`
- `execution_instance_ref`
- `binding_ref`
- `metric_name`
- `metric_type`
- `metric_value`
- `measured_at`
- `notes`

#### PluginTraceSlice

Fields:
- `trace_slice_id`
- `execution_instance_ref`
- `slice_type`
- `started_at`
- `ended_at`
- `event_refs`
- `metric_refs`
- `outcome_summary`

#### PluginExecutionOutcome

Fields:
- `outcome_id`
- `execution_instance_ref`
- `final_status`
- `final_output_present`
- `partial_output_present`
- `artifact_present`
- `failure_ref`
- `recovery_ref`
- `completed_at`
- `summary`

### 7.11 Governance objects

#### PluginRuntimeGovernancePosture

Fields:
- `governance_posture_id`
- `plugin_id`
- `target_runtime_ref`
- `artifact_ref`
- `manifest_ref`
- `current_posture`
- `trust_scope`
- `evidence_ref_set`
- `last_evaluated_at`
- `last_decision_ref`
- `notes`

#### PluginRuntimeGovernanceDecision

Fields:
- `decision_id`
- `plugin_id`
- `target_runtime_ref`
- `decision_type`
- `previous_posture`
- `new_posture`
- `decision_basis`
- `decided_at`
- `decided_by`
- `notes`

### 7.12 Lifecycle objects

#### PluginLifecycleState

Fields:
- `lifecycle_state_id`
- `plugin_id`
- `artifact_ref`
- `manifest_ref`
- `target_runtime_ref`
- `build_state`
- `publication_state`
- `installation_state`
- `binding_state`
- `current_execution_state`
- `governance_state`
- `last_transition_ref`
- `last_updated_at`
- `notes`

#### PluginLifecycleTransition

Fields:
- `transition_id`
- `plugin_id`
- `from_state_domain`
- `from_state`
- `to_state_domain`
- `to_state`
- `trigger_type`
- `trigger_ref`
- `occurred_at`
- `rationale_summary`

### 7.13 Classification objects

#### PluginClassificationRecord

Fields:
- `plugin_id`
- `requested_class`
- `approved_class`
- `policy_version`
- `mcp_spec_baseline_version`
- `mcp_compatibility_level`
- `runtime_authority_model`
- `exposed_mcp_capabilities`
- `adapter_ref`
- `notes`
- optional request/approval provenance refs

---

## 8. Persistence model

The implementation must not leave persistence implicit.
Use repository classes, but the first backend may be filesystem-based.

### 8.1 Required persistence roots

Use the following first implementation layout under a runtime data root:

```text
var/plugin_builder/
  requests/
  proposals/
  builds/
  candidates/
  verification_runs/

var/plugin_registry/
  entries/
  search_index/

var/plugin_runtime/
  installations/
  bindings/
  events/
  metrics/
  lifecycle/
  governance/
```

### 8.2 Persistence rules

- JSON for domain records
- filesystem directories for artifacts/packages
- append-only sub-records for events, metrics, transitions, and governance decisions
- no silent in-place mutation of historical records
- current posture/state objects may be rewritten only when backed by append-only transition records

### 8.3 Repository classes to create

Create repository interfaces plus filesystem backends for:

- `BuilderRequestRepository`
- `BuilderResultRepository`
- `ArtifactRepository`
- `RegistryEntryRepository`
- `InstallationRepository`
- `BindingRepository`
- `ObservabilityRepository`
- `GovernanceRepository`
- `LifecycleRepository`
- `ClassificationRepository`

---

## 9. Exact implementation phases

Implement in this order.
Do not rearrange casually.

### Phase 0 — Baseline freeze and scaffolding

#### Goal
Create the new package skeleton without changing runtime behavior.

#### Work
1. Create `src/plugins/` package and subpackages.
2. Add contract dataclasses/enums/serialization helpers.
3. Add repository interfaces.
4. Add compatibility adapters but do not wire them into production code yet.
5. If `src/contracts/spec_versions.py` does not exist, create it and register the plugin family specs there.

#### Files to create
- all package `__init__.py`
- `src/plugins/contracts/common_enums.py`
- `src/plugins/contracts/serialization.py`
- `src/contracts/spec_versions.py` if absent

#### Tests
- import tests for all new contract modules
- JSON round-trip tests for all core dataclasses
- spec-version sync tests for plugin family entries

#### Done criteria
- new package imports cleanly
- no runtime behavior changed yet
- test suite still passes

---

### Phase 1 — Builder proposal and orchestration layer

#### Goal
Implement the builder-facing request/result system and Designer intake normalization.

#### Work
1. Implement `DesignerPluginBuildProposal` and draft-spec objects.
2. Implement `PluginBuilderRequest`, `PluginBuilderSpec`, `PluginBuilderResult`, and `BuilderFinding`.
3. Implement `builder/intake_gate.py`.
4. Implement `builder/normalize.py` to convert intake draft -> canonical builder spec.
5. Implement `builder/modes.py` for mode semantics.
6. Implement `builder/service.py` skeleton with stage sequencing but no full generation yet.

#### Required behaviors
- reject ambiguous source requests
- reject proposal-space objects pretending to be trusted runtime objects
- preserve unresolved fields, ambiguity, and assumptions through normalization
- support all canonical build modes

#### Files to create
- `src/plugins/contracts/intake_types.py`
- `src/plugins/contracts/builder_types.py`
- `src/plugins/builder/intake_gate.py`
- `src/plugins/builder/normalize.py`
- `src/plugins/builder/modes.py`
- `src/plugins/builder/service.py`
- `src/plugins/builder/findings.py`

#### Tests
- intake acceptance/rejection tests
- normalization tests from draft -> canonical spec
- build mode legality tests
- source-type ambiguity tests

#### Done criteria
- builder can accept a proposal and emit a normalized preview-ready result
- no code generation yet required
- all stage reports and findings are structured

---

### Phase 2 — Namespace policy and classification layer

#### Goal
Implement explicit namespace request, approval, runtime enforcement policy objects, and classification records.

#### Work
1. Implement requested vs approved namespace policy objects.
2. Implement builder-stage namespace approval logic in `builder/validator.py`.
3. Implement classification record and MCP compatibility resolution.
4. Implement `classification/mcp_bridge.py` as a contract bridge, not yet a full protocol runtime.
5. Add validation rules for requested/approved separation.

#### Required behaviors
- unknown scope must not auto-promote to full authority
- approved policy must never contain unresolved/unknown scope
- runtime enforcement policy must be allow-list only
- requested and approved classification must remain distinct

#### Files to create
- `src/plugins/contracts/namespace_types.py`
- `src/plugins/contracts/classification_types.py`
- `src/plugins/builder/classification.py`
- `src/plugins/adapters/mcp_bridge.py`

#### Tests
- namespace request validation tests
- approval narrowing tests
- deny-list vs allow-list enforcement-preparation tests
- MCP classification legality matrix tests

#### Done criteria
- builder can produce approved namespace policy objects
- classification record can be emitted for artifacts/registry/runtime consumption

---

### Phase 3 — Template resolution, generation, artifact packaging, and manifest creation

#### Goal
Generate a canonical candidate artifact and manifest from a normalized builder spec.

#### Work
1. Implement `builder/template_resolver.py`.
2. Implement `builder/generator.py` that creates candidate source files.
3. Implement artifact/manifest contract objects.
4. Implement package layout generation.
5. Implement integrity/provenance metadata.
6. Emit artifact directory and manifest JSON.
7. Add bridge from new manifest to legacy `PluginManifestV1` where needed.

#### Required behaviors
- entrypoint must be explicit
- manifest must be mandatory
- approved namespace policy ref must be attached
- verification posture fields exist even before verification completes
- classification summary must be attached
- no manifestless executable candidate may exist

#### Files to create
- `src/plugins/contracts/artifact_types.py`
- `src/plugins/builder/template_resolver.py`
- `src/plugins/builder/generator.py`
- `src/plugins/builder/storage.py`
- `src/plugins/adapters/legacy_platform_bridge.py`

#### Existing files to modify
- `src/platform/plugin_definition.py`
- `src/platform/plugin_auto_loader.py`
- possibly `src/platform/plugin_discovery.py`

#### Tests
- artifact packaging tests
- manifest completeness tests
- entrypoint resolution tests
- candidate scaffold generation tests
- legacy manifest bridge tests

#### Done criteria
- builder can output `scaffold_generated` and `build_complete_unregistered`
- canonical artifact directory can be loaded by artifact repository

---

### Phase 4 — Validation layer

#### Goal
Implement builder validation as a real stage family.

#### Work
1. Implement `builder/validator.py`.
2. Validate builder spec shape.
3. Validate plugin contract completeness.
4. Validate namespace policy legality.
5. Validate side effect policy.
6. Validate dependency requirements.
7. Validate classification coherence.

#### Required behaviors
- `validation_failed` must block trust progression
- blocking vs warning findings must be explicit
- failure codes must remain machine-usable

#### Files to create
- `src/plugins/builder/validator.py`
- `src/plugins/contracts/registry_types.py` partial as needed for validation summaries

#### Tests
- malformed spec rejection
- illegal side-effect combinations
- unresolved plugin type rejection when required
- invalid namespace policy rejection
- dependency requirement failure tests

#### Done criteria
- builder can stop at validation with structured report
- builder can progress only when validation passes

---

### Phase 5 — Verification layer

#### Goal
Implement static verification and test verification.

#### Work
1. Implement verification requirement objects and posture objects.
2. Implement static load check.
3. Implement smoke execution check through PluginExecutor bridge.
4. Implement I/O contract check.
5. Implement template integrity check.
6. Implement policy alignment check.
7. Implement optional behavioral and negative-scope tests.
8. Record verification evidence and posture.

#### Files to create
- `src/plugins/contracts/verification_types.py`
- `src/plugins/builder/verifier.py`

#### Existing files to modify
- `src/platform/plugin_executor.py`
- `src/platform/plugin_result.py`

#### Tests
- one test per check family
- verification profile tests: light / standard / strict
- verified vs validated distinction tests
- partial verification behavior tests

#### Done criteria
- builder can emit `verification_failed` or verified posture explicitly
- verification evidence is persisted and referenced by artifact and registry

---

### Phase 6 — Registry publication layer

#### Goal
Implement canonical registry entries and publication rules.

#### Work
1. Implement registry entry object and filesystem persistence.
2. Implement publication rules and scopes.
3. Implement search/discovery over registry entry summaries.
4. Extend current plugin registry fingerprinting to consume canonical entries.
5. Keep old `PluginVersionRegistry` working via adapter or parallel compatibility path.

#### Files to create
- `src/plugins/contracts/registry_types.py`
- `src/plugins/registry/catalog.py`
- `src/plugins/registry/persistence.py`
- `src/plugins/registry/search.py`
- `src/plugins/registry/fingerprint.py`
- `src/plugins/builder/registrar.py`

#### Existing files to modify
- `src/engine/plugin_registry_fingerprint.py`
- `src/platform/plugin_version_registry.py`

#### Tests
- registry draft/published/suspended/deprecated/withdrawn transitions
- search by name/category/keyword/scope/readiness/policy sensitivity
- publication requires artifact + manifest + verification + policy posture
- publication does not imply installation

#### Done criteria
- `build_and_register` mode works end to end
- canonical registry entries exist and are queryable

---

### Phase 7 — Installation and loading layer

#### Goal
Implement explicit installation state and runtime preflight.

#### Work
1. Implement `PluginInstallationState`.
2. Implement installation service.
3. Implement runtime preflight for artifact integrity, entrypoint, compatibility, verification posture, policy readiness, dependency readiness, governance check.
4. Implement classification-aware loading, including unresolved plugin_type rejection.
5. Support install-but-not-active, loaded-but-not-active, suspended, removed states.

#### Files to create
- `src/plugins/contracts/installation_types.py`
- `src/plugins/runtime/installation.py`
- `src/plugins/runtime/loader.py`
- `src/plugins/runtime/compatibility.py`

#### Existing files to modify
- `src/platform/plugin_auto_loader.py`
- `src/platform/plugin_discovery.py`

#### Tests
- publication != installation tests
- verification posture gating tests
- unresolved plugin_type load rejection tests
- classification-aware preflight tests for internal_native / mcp_native / hybrid / adapter

#### Done criteria
- plugin can be installed, loaded, activated, suspended, removed through explicit state changes

---

### Phase 8 — Runtime binding and execution instance layer

#### Goal
Bind installed plugins into explicit runtime execution objects.

#### Work
1. Implement `BoundPluginRuntime`.
2. Implement binding preconditions.
3. Implement execution instance model.
4. Bridge the existing `src/platform/plugin_executor.py` through the bound runtime object.
5. Ensure stage allowance and namespace policy are enforced before execution.

#### Files to create
- `src/plugins/contracts/binding_types.py`
- `src/plugins/runtime/binding.py`
- `src/plugins/runtime/execution.py`

#### Existing files to modify
- `src/platform/plugin_executor.py`

#### Tests
- installed-but-not-bindable tests
- binding_failed cases
- bound_ready cases
- stage-allowance enforcement tests
- executor routing must include bound policy and context declarations

#### Done criteria
- no active plugin executes anonymously
- execution always has `binding_ref` and `execution_instance_ref`

---

### Phase 9 — Context I/O layer

#### Goal
Make plugin execution interact with Working Context through explicit declared bindings.

#### Work
1. Implement context input extraction.
2. Implement normalized payload creation.
3. Implement output emission rules.
4. Separate partial output vs final output vs artifact emission.
5. Block undeclared or disallowed writes.

#### Files to create
- `src/plugins/contracts/context_io_types.py`
- `src/plugins/runtime/context_io.py`

#### Existing files to modify
- `src/platform/plugin_result.py`
- `src/platform/plugin.py` only if needed via adapter, not by large rewrite

#### Tests
- allowed read extraction tests
- disallowed read/write blocking tests
- partial vs final output tests
- malformed output handling tests
- artifact emission linkage tests

#### Done criteria
- plugin I/O is fully context-mediated and traceable

---

### Phase 10 — Failure / recovery layer

#### Goal
Implement canonical failure and recovery records.

#### Work
1. Implement failure categories.
2. Implement retryability rules.
3. Implement partial outcome rules.
4. Implement timeout/cancellation handling.
5. Implement recovery actions.
6. Implement escalation rules and repeated failure posture triggers.

#### Files to create
- `src/plugins/contracts/failure_types.py`
- `src/plugins/runtime/failure_recovery.py`

#### Tests
- retryable vs non-retryable failure tests
- partial outcome retention tests
- timeout and cancellation tests
- repeated failure -> posture change tests

#### Done criteria
- every failed execution instance emits explicit failure state and optional recovery state

---

### Phase 11 — Observability layer

#### Goal
Implement events, metrics, trace slices, and final outcome signals.

#### Work
1. Emit runtime events for lifecycle, context I/O, artifacts, warnings, failures, recoveries.
2. Emit metrics for duration, size, resource usage, stability.
3. Emit trace slices by phase.
4. Emit final outcome signal.
5. Provide repository queries for timeline/trace panels and diagnostics.

#### Files to create
- `src/plugins/contracts/observability_types.py`
- `src/plugins/runtime/observability.py`

#### Existing files to modify
- `src/server/public_plugin_runtime.py`
- possible trace-view integration files later

#### Tests
- event family coverage tests
- metric emission tests
- trace slice assembly tests
- final outcome signal tests

#### Done criteria
- plugin execution is observable as engine truth, not inferred behavior

---

### Phase 12 — Governance and lifecycle layer

#### Goal
Implement runtime posture decisions and unified lifecycle state machine.

#### Work
1. Implement governance posture and governance decision objects.
2. Implement evidence aggregation.
3. Implement decision families maintain/promote/restrict/require_review/suspend/quarantine/remove/restore.
4. Implement lifecycle state object and transitions.
5. Record all transitions append-only.
6. Enforce impossible state combinations.

#### Files to create
- `src/plugins/contracts/governance_types.py`
- `src/plugins/contracts/lifecycle_types.py`
- `src/plugins/runtime/governance.py`
- `src/plugins/runtime/lifecycle.py`

#### Tests
- governance posture transition tests
- illegal lifecycle combination tests
- transition recording tests
- evidence-driven promote/restrict/suspend/quarantine tests

#### Done criteria
- plugin trust maintenance is explicit, queryable, and transition-based

---

### Phase 13 — Classification and MCP compatibility layer

#### Goal
Implement requested/approved classification and MCP compatibility consumption at publication/load time.

#### Work
1. Implement classification record object.
2. Add builder-stage classification approval logic.
3. Add manifest summary fields.
4. Add registry posture exposure.
5. Add loading/install preflight classification consumption.
6. Add adapter rules for MCP-facing surfaces without replacing internal runtime truth.

#### Files to create
- `src/plugins/contracts/classification_types.py`
- `src/plugins/classification/classifier.py`
- `src/plugins/adapters/mcp_bridge.py`

#### Tests
- requested vs approved classification separation tests
- compatibility level tests (`none`, `mcp_wrapped`, `mcp_partial`, `mcp_native`)
- runtime authority model legality tests
- adapter boundary tests

#### Done criteria
- classification is fully integrated into builder, artifact, registry, and loading preflight

---

### Phase 14 — Server/public/manual builder surfaces

#### Goal
Expose the builder system to the rest of Nexa without violating trust boundaries.

#### Work
1. Add server-facing models for builder requests and summaries.
2. Add runtime functions for builder preview/build/register flows.
3. Add thin routes if current server architecture expects them.
4. Support caller types `designer_flow`, `manual_builder_ui`, `automation_flow`, and `admin_flow`.
5. Do not implement a heavy UI yet; only a minimal server/public contract.

#### Files to create
- `src/server/plugin_builder_models.py`
- `src/server/plugin_builder_runtime.py`
- `src/server/plugin_builder_routes.py`

#### Existing files to modify
- `src/server/public_plugin_models.py`
- `src/server/public_plugin_runtime.py`

#### Tests
- public/server model serialization tests
- manual-builder preview flow tests
- designer-driven proposal handoff tests
- registration/install-after-register flow tests

#### Done criteria
- other Nexa subsystems can call the builder through one explicit service boundary

---

## 10. Migration strategy for existing `src/platform` code

The implementation must not break the current plugin runtime while introducing the new builder family.

### 10.1 Preserve and bridge, then converge

Keep current files but gradually route them through new contract-aware layers.

#### Immediate bridge mapping

- `src/platform/plugin_version_registry.py`
  - keep current `PluginRegistry` API for existing tests
  - add adapter to/from `PluginRegistryEntry`

- `src/platform/plugin_executor.py`
  - keep execution entry helpers
  - internally route through `BoundPluginRuntime` and execution instance logic

- `src/platform/plugin_auto_loader.py`
  - keep entry loading helper
  - route load preflight through new installation/loading layer when a canonical artifact is involved

- `src/platform/plugin_result.py`
  - normalize raw runtime output into `PluginContextOutput` / `PluginExecutionOutcome` friendly structures

### 10.2 Do not do these migrations in the first pass

Do not immediately:
- delete old `PluginManifestV1`
- rewrite all old tests to new dataclasses
- require all existing simple plugins to be repackaged before the adapter path exists

### 10.3 Required compatibility behavior

The old path must still work for:
- step-based plugin tests
- simple registry resolution tests
- plugin executor tests
- existing external plugin loading tests

until the bridge layer is proven.

---

## 11. Test plan

This is the minimum test suite structure required.

### 11.1 New test directories

```text
tests/plugins/
  test_plugin_builder_request_contract.py
  test_plugin_builder_normalization.py
  test_plugin_builder_modes.py
  test_plugin_builder_generation.py
  test_plugin_builder_validation.py
  test_plugin_builder_verification.py
  test_plugin_builder_registration.py
  test_plugin_namespace_policy.py
  test_plugin_artifact_manifest.py
  test_plugin_installation_loading.py
  test_plugin_runtime_binding.py
  test_plugin_context_io.py
  test_plugin_failure_recovery.py
  test_plugin_runtime_observability.py
  test_plugin_runtime_governance.py
  test_plugin_lifecycle_state_machine.py
  test_plugin_classification_mcp.py
  test_plugin_server_builder_surface.py
```

### 11.2 Existing tests that must stay green

At minimum keep green:

- `tests/test_plugin_contract.py`
- `tests/test_step82_plugin_registry.py`
- `tests/test_step83_plugin_registry_resolution_in_negotiate.py`
- `tests/test_step146_plugin_auto_loader.py`
- `tests/test_step157_plugin_metadata_validation.py`
- `tests/test_step193_savefile_plugin_loader_convergence.py`
- `tests/test_step194_savefile_executor_plugin_path_contract.py`
- `tests/test_step196_plugin_boundary_unification.py`
- `tests/test_step42_external_plugin_loading.py`
- `tests/test_step43_external_plugin_sandbox.py`
- `tests/test_file_write_plugin_contract.py`
- `tests/test_platform_input_reader_plugins.py`

### 11.3 Required test families by feature

#### Builder/intake
- legal/illegal request combinations
- preview_only behavior
- build_and_register behavior
- revalidate_existing behavior
- proposal blocked vs clarification_required behavior

#### Namespace policy
- unknown scope rejection
- read/write distinction
- external target policy
- runtime enforcement allow-list behavior

#### Artifact/manifest
- explicit entrypoint required
- manifest required
- integrity metadata present
- provenance metadata present
- verification posture and namespace policy ref attached

#### Verification
- validated != verified
- all check families report explicitly
- strict profile blocks weaker evidence

#### Registry
- publication scope explicit
- visibility != installability
- search returns registry entries, not raw artifact internals

#### Runtime
- install/load/activate states separate
- classification-aware preflight
- unresolved plugin_type blocks activation
- executor always has bound policy + context declarations

#### Failure/recovery
- every failure emits canonical state
- retryability rules work
- partial outcomes preserved according to rules
- repeated failure can cause posture change

#### Observability
- event family coverage
- metric family coverage
- trace slice completeness
- final outcome signal correctness

#### Governance/lifecycle
- explicit transitions only
- impossible state combinations rejected
- promote/restrict/suspend/quarantine/remove/restore all recorded

---

## 12. Recommended implementation batches

For execution efficiency, use these grouped batches instead of one-file-at-a-time work.

### Batch A — Scaffolding + contract dataclasses
- Phase 0
- start of Phase 1

### Batch B — Intake + normalization + builder service skeleton
- remainder of Phase 1

### Batch C — Namespace policy + classification
- Phase 2

### Batch D — Generation + artifact + manifest
- Phase 3

### Batch E — Validation + verification
- Phases 4 and 5 together

### Batch F — Registry publication + compatibility bridge
- Phase 6

### Batch G — Installation + loading + binding
- Phases 7 and 8 together

### Batch H — Context I/O + failure/recovery + observability
- Phases 9, 10, 11 together

### Batch I — Governance + lifecycle + classification completion
- Phases 12 and 13 together

### Batch J — Server surface integration
- Phase 14

This batching is recommended because these groups are structurally coupled.

---

## 13. Explicit implementation rules

### 13.1 Do not flatten proposal, candidate, artifact, registry entry, installation state, and runtime binding into one blob
These are distinct truth layers.

### 13.2 Do not let registration bypass verification posture
Even if build succeeded, registration must still check required posture.

### 13.3 Do not let runtime load raw source without canonical artifact/manifest path when using the new builder path
Legacy direct-loading may remain temporarily for backward compatibility, but the new path must be artifact-driven.

### 13.4 Do not let approved namespace policy be inferred from requested scope
Approval must be explicit.

### 13.5 Do not let UI/server/public wording redefine engine truth
Public surfaces may summarize; engine/runtime records must remain exact.

### 13.6 Do not silently collapse MCP concepts into internal runtime concepts
Classification and adapter boundaries must stay explicit.

### 13.7 Do not delete existing plugin tests until their equivalent contract coverage clearly exists
Migration without coverage is forbidden.

---

## 14. Completion definition

The Plugin Builder is considered fully implemented only when all of the following are true.

### 14.1 Builder completeness
- a designer proposal can become a builder request
- builder can preview, scaffold, validate, verify, build, and register
- result object is explicit and stage-complete

### 14.2 Artifact completeness
- canonical artifact + manifest can be generated and persisted
- entrypoint, provenance, integrity, namespace policy, verification posture, and classification are all represented

### 14.3 Registry completeness
- canonical registry entries exist
- publication scope, visibility, policy posture, verification posture, and provenance are explicit
- search and fingerprinting work

### 14.4 Runtime completeness
- install, load, activate, bind, execute, fail, recover, observe, govern, and transition are all represented by explicit state objects

### 14.5 Governance completeness
- posture changes are evidence-driven and recorded
- lifecycle transitions are explicit and queryable

### 14.6 Classification completeness
- requested vs approved classification is explicit
- MCP compatibility level and runtime authority model are represented and consumed by runtime preflight

### 14.7 Backward compatibility completeness
- existing plugin/runtime tests still pass or are replaced by clearly stronger equivalents with intentional migration documentation

### 14.8 Documentation completeness
- code paths and object names match the plugin contract family docs
- any divergence is documented explicitly

---

## 15. Final execution advice for the implementing AI

When implementing from this plan:

1. start with new `src/plugins/` contract models and repositories
2. keep current `src/platform/` behavior working through adapters
3. implement the builder as a stage-orchestrated service, not a monolith
4. persist explicit records for every stage and every transition
5. add tests before wide integration rewrites
6. do not treat registry publication or runtime loading as trivial consequences of build success
7. do not skip observability/governance/lifecycle just because generation works
8. do not let MCP compatibility contaminate internal runtime identity

If these rules are followed, another AI can implement the full plugin builder system without drifting away from the uploaded contract family.

---

## 16. Implementation done checklist

A batch is only done if all boxes below are true for the targeted phase.

- [ ] all new dataclasses/enums serialize and deserialize cleanly
- [ ] all required repositories exist
- [ ] all targeted phase tests pass
- [ ] no targeted state transition is implicit
- [ ] no proposal-space object is misused as runtime truth
- [ ] no approved namespace policy is inferred from requested scope
- [ ] no artifact lacks manifest/entrypoint/provenance/integrity references
- [ ] no runtime execution occurs without explicit binding/execution-instance identity
- [ ] no failure is silent
- [ ] no governance posture change lacks evidence and recorded decision
- [ ] lifecycle transitions are append-only and queryable
- [ ] backward compatibility path still works

## 17. Final statement

The correct implementation of the Plugin Builder is not:

- a plugin code generator
- a registry wrapper
- a runtime loader only
- a UI flow only

It is a full governed plugin construction, publication, runtime, and trust-maintenance system.

That is the implementation meaning of the uploaded plugin builder specification family.
