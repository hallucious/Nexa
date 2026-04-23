Spec ID: spec_catalog
Version: 1.0.0
Status: Partial
Category: indexes
Depends On:

# NEXA SPEC CATALOG

## Purpose

This document provides a compact index of the major Nexa spec groups.
It distinguishes between the active YAML-backed spec core and the supporting storage / format reference set.

## 1. Active YAML-Backed Spec Core

| Spec | Category | Purpose |
|---|---|---|
| terminology | foundation | shared language |
| execution_model | architecture | execution-engine model |
| trace_model | architecture | trace structure |
| node_abstraction | architecture | node as sole execution unit |
| node_execution_contract | architecture | runtime contract per node |
| circuit_contract | architecture | circuit structure and execution boundaries |
| universal_provider_architecture | architecture | provider system architecture |
| execution_environment_contract | contracts | execution environment contract |
| provider_contract | contracts | provider interface |
| plugin_contract | contracts | plugin behavior contract |
| plugin_registry_contract | contracts | plugin discovery and registry rules |
| prompt_contract | contracts | prompt execution interface |
| validation_engine_contract | contracts | validation system |
| execution_config_canonicalization_contract | contracts | config normalization |
| execution_config_schema_contract | contracts | config schema |
| context_key_schema_contract | contracts | working-context key namespace |
| validation_rule_catalog | policies | rule inventory |
| validation_rule_lifecycle | policies | rule lifecycle |
| spec_catalog | indexes | spec index |
| spec_dependency_map | indexes | dependency index |
| execution_config_prompt_binding_contract | execution_config | prompt binding contract |
| execution_config_registry_contract | execution_config | config registry contract |

## 2. Supporting Storage / Format Reference Set

| Spec | Category | Purpose |
|---|---|---|
| storage_architecture_overview | storage | three-layer storage overview |
| storage_lifecycle_spec | storage | save / commit / execute lifecycle |
| working_save_spec | storage | editable present-state storage layer |
| commit_snapshot_spec | storage | approval-gated structural anchor |
| execution_record_spec | storage | run-scoped historical artifact |
| storage_format_mapping_spec | storage | lifecycle-to-format mapping |
| nex_unified_schema | formats | unified `.nex` family schema |
| nex_parser_validator_branch_rules | formats | role-aware parser / validator branching |
| nex_typed_model_spec | formats | typed model split for `.nex` roles |
| nex_load_validate_api_spec | formats | public load / validate API shape |

## 3. Decision

The active YAML-backed spec core remains the authoritative contract set for synchronization tests.
The storage / format documents are the current supporting reference set for three-layer storage-sector documentation sync.


## 4. Supporting UI / Editor / Localization Reference Set

| Spec | Category | Purpose |
|---|---|---|
| ui_architecture_package | ui | overall UI shell / module-slot architecture |
| ui_adapter_view_model_contract | ui | engine-to-UI adapter boundary |
| graph_workspace_view_model_spec | ui | graph workspace view model |
| inspector_panel_view_model_spec | ui | inspector detail view model |
| validation_panel_view_model_spec | ui | validation findings projection |
| execution_panel_view_model_spec | ui | execution state projection |
| designer_panel_view_model_spec | ui | proposal-flow projection |
| trace_timeline_viewer_view_model_spec | ui | temporal observability projection |
| artifact_viewer_view_model_spec | ui | artifact inspection projection |
| storage_panel_view_model_spec | ui | storage lifecycle projection |
| diff_viewer_view_model_spec | ui | comparison / diff projection |
| theme_layout_layer_spec | ui | visual / layout layer rules |
| ui_state_ownership_and_persistence_spec | ui | UI-owned state boundary |
| ui_section_schema_spec | ui | `.nex.ui` schema |
| ui_section_branch_rules_spec | ui | role-aware `.nex.ui` handling |
| ui_public_api_exposure_spec | ui | public API exposure of `.nex.ui` |
| ui_commit_boundary_stripping_spec | ui | commit-boundary stripping rules |
| ui_i18n_spec_index | ui/i18n | index for multilingual UI bundle |
| ui_i18n_bundle_manifest | ui/i18n | bundle manifest and placement guide |
| ui_multilingual_localization_architecture | ui/i18n | multilingual UI architecture |
| ui_language_settings_contract | ui/i18n | app / AI / format language settings |
| i18n_resource_schema_spec | ui/i18n | translation resource structure |
| ui_i18n_fallback_behavior_spec | ui/i18n | deterministic fallback rules |
| localized_message_resolution_spec | ui/i18n | localized message lookup path |
| validation_reason_code_localization_spec | ui/i18n | reason-code localization mapping |
| ai_response_language_policy_spec | ui/i18n | AI response language policy |
| ui_i18n_persistence_boundary_spec | ui/i18n | i18n persistence boundary |
| localization_test_strategy_spec | ui/i18n | localization validation strategy |

## 5. Decision

The UI / editor / localization documents are currently a supporting reference branch.
They guide architecture and future implementation, but they must not be added to the YAML-backed active spec core until code, public contracts, and automated tests are synchronized with them.
