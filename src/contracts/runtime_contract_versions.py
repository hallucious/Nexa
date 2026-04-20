from __future__ import annotations

"""Runtime-facing contract/spec version constants.

This module exists so runtime code can depend on stable literal version constants
without importing the broader documentation registry.
"""

# Keep these as literal string constants because some tests regex-match them directly.
ENGINE_EXECUTION_MODEL_VERSION = "1.12.0"
ENGINE_TRACE_MODEL_VERSION = "1.9.0"
VALIDATION_ENGINE_CONTRACT_VERSION = "2.0.0"
VALIDATION_RULE_CATALOG_VERSION = "2.0.0"
VALIDATION_RULE_LIFECYCLE_VERSION = "1.0.0"
EXECUTION_ENVIRONMENT_CONTRACT_VERSION = "1.4.0"
GRAPH_EXECUTION_CONTRACT_VERSION = "1.0.0"
CIRCUIT_RUNTIME_MODEL_VERSION = "1.0.0"
CONTEXT_KEY_SCHEMA_CONTRACT_VERSION = "1.1.0"
