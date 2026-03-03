# Spec ↔ Code Version Sync Constants
# This module belongs to the contracts layer (not runtime logic).

ENGINE_EXECUTION_MODEL_VERSION = "1.6.0"
ENGINE_TRACE_MODEL_VERSION = "1.4.0"
VALIDATION_ENGINE_CONTRACT_VERSION = "1.2.0"
VALIDATION_RULE_CATALOG_VERSION = "1.1.0"
VALIDATION_RULE_LIFECYCLE_VERSION = "1.0.0"
EXECUTION_ENVIRONMENT_CONTRACT_VERSION = "1.4.0"

# Canonical mapping: doc-relative-path -> version constant
# Used by the spec-version sync contract test to enforce completeness.
SPEC_VERSIONS = {
    "docs/specs/terminology.md": "1.0.1",
    "docs/specs/execution_model.md": ENGINE_EXECUTION_MODEL_VERSION,
    "docs/specs/trace_model.md": ENGINE_TRACE_MODEL_VERSION,
    "docs/specs/node_abstraction.md": "1.1.0",
    "docs/specs/node_execution_contract.md": "1.1.0",
    "docs/specs/provider_contract.md": "1.1.0",
    "docs/specs/universal_provider_architecture.md": "1.0.0",
    "docs/specs/circuit_contract.md": "1.1.0",
    "docs/specs/validation_engine_contract.md": VALIDATION_ENGINE_CONTRACT_VERSION,
    "docs/specs/validation_rule_catalog.md": VALIDATION_RULE_CATALOG_VERSION,
    # Non-active specs may still be versioned here to enable strict checks when activated.
    "docs/specs/validation_rule_lifecycle.md": VALIDATION_RULE_LIFECYCLE_VERSION,
    "docs/specs/execution_environment_contract.md": EXECUTION_ENVIRONMENT_CONTRACT_VERSION,
}
