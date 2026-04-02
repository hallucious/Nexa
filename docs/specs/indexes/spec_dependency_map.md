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
