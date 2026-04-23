Spec ID: spec_dependency_map
Version: 1.0.0
Status: Partial
Category: indexes
Depends On:

# NEXA SPEC DEPENDENCY MAP

## Purpose

Defines the main dependency relationships between the active spec core and the supporting storage / format reference set.

## 1. Active Spec Core

terminology
 ↓
execution_model
 ↓
node_abstraction
 ↓
node_execution_contract
 ↓
circuit_contract

terminology
 ↓
trace_model

execution_environment_contract
 ↓
provider_contract
 ↓
prompt_contract
 ↓
plugin_contract
 ↓
plugin_registry_contract

execution_config_schema_contract
 ↓
execution_config_canonicalization_contract
 ↓
execution_config_registry_contract
 ↓
execution_config_prompt_binding_contract

validation_engine_contract
 ↓
validation_rule_catalog
 ↓
validation_rule_lifecycle

## 2. Supporting Storage / Format Set

storage_architecture_overview
 ↓
storage_lifecycle_spec
 ↓
working_save_spec
 ↓
commit_snapshot_spec
 ↓
execution_record_spec

storage_architecture_overview
 ↓
storage_format_mapping_spec
 ↓
nex_unified_schema
 ↓
nex_parser_validator_branch_rules
 ↓
nex_typed_model_spec
 ↓
nex_load_validate_api_spec

## 3. Bridge Rule

The storage / format set depends on the active execution-model and trace-model vocabulary, but is currently maintained as a supporting reference branch rather than part of the YAML-backed active spec core.


## 4. Supporting UI / I18n Dependency Branch

ui_architecture_package
 ↓
ui_adapter_view_model_contract
 ↓
graph_workspace_view_model_spec
 ↓
inspector_panel_view_model_spec
 ↓
validation_panel_view_model_spec
 ↓
execution_panel_view_model_spec
 ↓
designer_panel_view_model_spec

ui_architecture_package
 ↓
trace_timeline_viewer_view_model_spec
 ↓
artifact_viewer_view_model_spec
 ↓
storage_panel_view_model_spec
 ↓
diff_viewer_view_model_spec

ui_architecture_package
 ↓
theme_layout_layer_spec
 ↓
ui_state_ownership_and_persistence_spec
 ↓
ui_section_schema_spec
 ↓
ui_section_branch_rules_spec
 ↓
ui_public_api_exposure_spec
 ↓
ui_commit_boundary_stripping_spec

ui_architecture_package
 ↓
ui_multilingual_localization_architecture
 ↓
ui_language_settings_contract
 ↓
i18n_resource_schema_spec
 ↓
ui_i18n_fallback_behavior_spec
 ↓
localized_message_resolution_spec
 ↓
validation_reason_code_localization_spec

ui_language_settings_contract
 ↓
ai_response_language_policy_spec

ui_state_ownership_and_persistence_spec
 ↓
ui_i18n_persistence_boundary_spec

ui_multilingual_localization_architecture
 ↓
localization_test_strategy_spec

## 5. Bridge Rule

The UI / i18n branch depends on the execution-model, storage-lifecycle, and UI-owned-state boundaries, but remains a supporting reference branch until implementation and contract tests converge.
