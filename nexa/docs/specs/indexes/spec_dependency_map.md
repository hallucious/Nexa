Spec ID: spec_dependency_map
Version: 2.0.0
Status: Active
Category: indexes

# Nexa Specification Dependency Map

## Purpose

Defines the dependency relationships between active Nexa specification documents.

Only active and implemented specifications are included.

---

## Dependency Principles

1. Dependencies represent **contract requirements**, not execution order.
2. Pipeline-style dependency interpretation is strictly forbidden.
3. All dependencies MUST reflect actual code-level coupling.

---

## Foundation Layer

terminology
→ (used by all specs)

---

## Architecture Layer

execution_model
→ node_abstraction
→ node_execution_contract
→ circuit_contract
→ trace_model

universal_provider_architecture
→ provider_contract

---

## Contracts Layer

execution_environment_contract

prompt_contract
provider_contract
plugin_contract
plugin_registry_contract

context_key_schema_contract
→ (used by all runtime-related specs)

execution_config_schema_contract
→ execution_config_canonicalization_contract
→ execution_config_registry_contract
→ execution_config_prompt_binding_contract

validation_engine_contract
→ validation_rule_catalog
→ validation_rule_lifecycle

---

## Cross-Cutting Dependencies

node_execution_contract
→ execution_environment_contract
→ trace_model

plugin_contract
→ context_key_schema_contract

provider_contract
→ execution_environment_contract

execution_model
→ circuit_contract
→ node_execution_contract

---

## Source of Truth

docs/specs/_active_specs.yaml

---

## Synchronization Rule

This document MUST be updated when:

- a spec is added or removed
- dependency relationships change
- execution model structure changes

---

End of Specification Dependency Map