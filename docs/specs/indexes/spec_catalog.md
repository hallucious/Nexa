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
