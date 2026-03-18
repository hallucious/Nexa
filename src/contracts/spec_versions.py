# Spec ↔ Code Version Sync Constants
# This module belongs to the contracts layer (not runtime logic).

ENGINE_EXECUTION_MODEL_VERSION = "1.6.0"
ENGINE_TRACE_MODEL_VERSION = "1.4.0"
VALIDATION_ENGINE_CONTRACT_VERSION = "2.0.0"
VALIDATION_RULE_CATALOG_VERSION = "2.0.0"
VALIDATION_RULE_LIFECYCLE_VERSION = "1.0.0"
EXECUTION_ENVIRONMENT_CONTRACT_VERSION = "1.4.0"

# Step115 new specs
GRAPH_EXECUTION_CONTRACT_VERSION = "1.0.0"
CIRCUIT_RUNTIME_MODEL_VERSION = "1.0.0"

# Step179 new spec
CONTEXT_KEY_SCHEMA_CONTRACT_VERSION = "1.0.0"

SPEC_VERSIONS = {
    "docs/specs/terminology.md": "1.0.1",
    "docs/specs/docs_specs_circuit_trace_contract.md": "1.0.0",
    "docs/specs/observability_metrics.md": "1.0.0",
    "docs/specs/plugin_contract.md": "1.1.0",
    "docs/specs/plugin_registry_contract.md": "1.0.0",
    "docs/specs/prompt_contract.md": "1.0.0",
    "docs/specs/execution_model.md": ENGINE_EXECUTION_MODEL_VERSION,
    "docs/specs/trace_model.md": ENGINE_TRACE_MODEL_VERSION,
    "docs/specs/node_abstraction.md": "1.1.0",
    "docs/specs/node_execution_contract.md": "1.1.0",
    "docs/specs/provider_contract.md": "1.1.0",
    "docs/specs/universal_provider_architecture.md": "1.0.0",
    "docs/specs/circuit_contract.md": "1.1.0",
    "docs/specs/validation_engine_contract.md": VALIDATION_ENGINE_CONTRACT_VERSION,
    "docs/specs/validation_rule_catalog.md": VALIDATION_RULE_CATALOG_VERSION,
    "docs/specs/validation_rule_lifecycle.md": VALIDATION_RULE_LIFECYCLE_VERSION,
    "docs/specs/execution_environment_contract.md": EXECUTION_ENVIRONMENT_CONTRACT_VERSION,
    "docs/specs/graph_execution_contract.md": GRAPH_EXECUTION_CONTRACT_VERSION,
    "docs/specs/circuit_runtime_model.md": CIRCUIT_RUNTIME_MODEL_VERSION,

    "docs/specs/foundation/terminology.md": "1.0.1",

    "docs/specs/contracts/execution_environment_contract.md": "1.4.0",
    "docs/specs/contracts/execution_config_canonicalization_contract.md": "1.0.0",
    "docs/specs/contracts/execution_config_schema_contract.md": "1.0.0",
    "docs/specs/contracts/context_key_schema_contract.md": CONTEXT_KEY_SCHEMA_CONTRACT_VERSION,
    "docs/specs/contracts/plugin_contract.md": "1.1.0",
    "docs/specs/contracts/plugin_registry_contract.md": "1.0.0",
    "docs/specs/contracts/prompt_contract.md": "1.0.0",
    "docs/specs/contracts/provider_contract.md": "1.1.0",
    "docs/specs/contracts/validation_engine_contract.md": VALIDATION_ENGINE_CONTRACT_VERSION,

    "docs/specs/policies/validation_rule_catalog.md": VALIDATION_RULE_CATALOG_VERSION,
    "docs/specs/policies/validation_rule_lifecycle.md": VALIDATION_RULE_LIFECYCLE_VERSION,

    "docs/specs/architecture/circuit_contract.md": "1.1.0",
    "docs/specs/architecture/node_abstraction.md": "1.1.0",
    "docs/specs/architecture/node_execution_contract.md": "1.1.0",
    "docs/specs/architecture/execution_model.md": ENGINE_EXECUTION_MODEL_VERSION,
    "docs/specs/architecture/trace_model.md": ENGINE_TRACE_MODEL_VERSION,
    "docs/specs/architecture/universal_provider_architecture.md": "1.0.0",

    "docs/specs/execution_config_prompt_binding_contract.md": "1.0.0",
    "docs/specs/execution_config_registry_contract.md": "1.0.0",

    "docs/specs/indexes/spec_catalog.md": "1.0.0",
    "docs/specs/indexes/spec_dependency_map.md": "2.0.0",
}
