from __future__ import annotations

import re
from pathlib import Path

from src.contracts.runtime_contract_versions import (
    CIRCUIT_RUNTIME_MODEL_VERSION,
    CONTEXT_KEY_SCHEMA_CONTRACT_VERSION,
    ENGINE_EXECUTION_MODEL_VERSION,
    ENGINE_TRACE_MODEL_VERSION,
    EXECUTION_ENVIRONMENT_CONTRACT_VERSION,
    GRAPH_EXECUTION_CONTRACT_VERSION,
    VALIDATION_ENGINE_CONTRACT_VERSION,
    VALIDATION_RULE_CATALOG_VERSION,
    VALIDATION_RULE_LIFECYCLE_VERSION,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _extract_version(rel_path: str, default: str) -> str:
    path = _REPO_ROOT / rel_path
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return default

    m = re.search(r"^Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", text, flags=re.MULTILINE)
    if m:
        return m.group(1)

    m2 = re.search(r"^-\s*Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", text, flags=re.MULTILINE)
    if m2:
        return m2.group(1)

    return default


SPEC_VERSIONS = {
    # legacy / compatibility paths
    "docs/specs/terminology.md": _extract_version("docs/specs/terminology.md", "1.0.1"),
    "docs/specs/docs_specs_circuit_trace_contract.md": _extract_version("docs/specs/docs_specs_circuit_trace_contract.md", "1.0.0"),
    "docs/specs/observability_metrics.md": _extract_version("docs/specs/observability_metrics.md", "1.0.0"),
    "docs/specs/plugin_contract.md": _extract_version("docs/specs/plugin_contract.md", "1.1.0"),
    "docs/specs/plugin_registry_contract.md": _extract_version("docs/specs/plugin_registry_contract.md", "1.0.0"),
    "docs/specs/prompt_contract.md": _extract_version("docs/specs/prompt_contract.md", "1.0.0"),
    "docs/specs/execution_model.md": _extract_version("docs/specs/execution_model.md", ENGINE_EXECUTION_MODEL_VERSION),
    "docs/specs/trace_model.md": _extract_version("docs/specs/trace_model.md", ENGINE_TRACE_MODEL_VERSION),
    "docs/specs/node_abstraction.md": _extract_version("docs/specs/node_abstraction.md", "1.0.0"),
    "docs/specs/node_execution_contract.md": _extract_version("docs/specs/node_execution_contract.md", "1.0.0"),
    "docs/specs/provider_contract.md": _extract_version("docs/specs/provider_contract.md", "1.1.0"),
    "docs/specs/universal_provider_architecture.md": _extract_version("docs/specs/universal_provider_architecture.md", "1.0.0"),
    "docs/specs/circuit_contract.md": _extract_version("docs/specs/circuit_contract.md", "1.0.0"),
    "docs/specs/validation_engine_contract.md": _extract_version("docs/specs/validation_engine_contract.md", VALIDATION_ENGINE_CONTRACT_VERSION),
    "docs/specs/graph_execution_contract.md": _extract_version("docs/specs/graph_execution_contract.md", GRAPH_EXECUTION_CONTRACT_VERSION),
    "docs/specs/circuit_runtime_model.md": _extract_version("docs/specs/circuit_runtime_model.md", CIRCUIT_RUNTIME_MODEL_VERSION),

    # active structured paths
    "docs/specs/foundation/terminology.md": _extract_version("docs/specs/foundation/terminology.md", "1.0.1"),

    "docs/specs/contracts/execution_environment_contract.md": _extract_version("docs/specs/contracts/execution_environment_contract.md", EXECUTION_ENVIRONMENT_CONTRACT_VERSION),
    "docs/specs/contracts/execution_config_canonicalization_contract.md": _extract_version("docs/specs/contracts/execution_config_canonicalization_contract.md", "1.0.0"),
    "docs/specs/contracts/execution_config_schema_contract.md": _extract_version("docs/specs/contracts/execution_config_schema_contract.md", "1.0.0"),
    "docs/specs/contracts/context_key_schema_contract.md": _extract_version("docs/specs/contracts/context_key_schema_contract.md", CONTEXT_KEY_SCHEMA_CONTRACT_VERSION),
    "docs/specs/contracts/plugin_contract.md": _extract_version("docs/specs/contracts/plugin_contract.md", "1.1.0"),
    "docs/specs/contracts/plugin_registry_contract.md": _extract_version("docs/specs/contracts/plugin_registry_contract.md", "1.0.0"),
    "docs/specs/contracts/prompt_contract.md": _extract_version("docs/specs/contracts/prompt_contract.md", "1.0.0"),
    "docs/specs/contracts/provider_contract.md": _extract_version("docs/specs/contracts/provider_contract.md", "1.1.0"),
    "docs/specs/contracts/validation_engine_contract.md": _extract_version("docs/specs/contracts/validation_engine_contract.md", VALIDATION_ENGINE_CONTRACT_VERSION),

    "docs/specs/policies/validation_rule_catalog.md": _extract_version("docs/specs/policies/validation_rule_catalog.md", VALIDATION_RULE_CATALOG_VERSION),
    "docs/specs/policies/validation_rule_lifecycle.md": _extract_version("docs/specs/policies/validation_rule_lifecycle.md", VALIDATION_RULE_LIFECYCLE_VERSION),

    "docs/specs/architecture/circuit_contract.md": _extract_version("docs/specs/architecture/circuit_contract.md", "1.0.0"),
    "docs/specs/architecture/node_abstraction.md": _extract_version("docs/specs/architecture/node_abstraction.md", "1.0.0"),
    "docs/specs/architecture/node_execution_contract.md": _extract_version("docs/specs/architecture/node_execution_contract.md", "1.0.0"),
    "docs/specs/architecture/execution_model.md": _extract_version("docs/specs/architecture/execution_model.md", ENGINE_EXECUTION_MODEL_VERSION),
    "docs/specs/architecture/trace_model.md": _extract_version("docs/specs/architecture/trace_model.md", ENGINE_TRACE_MODEL_VERSION),
    "docs/specs/architecture/universal_provider_architecture.md": _extract_version("docs/specs/architecture/universal_provider_architecture.md", "1.0.0"),

    "docs/specs/execution_config_prompt_binding_contract.md": _extract_version("docs/specs/execution_config_prompt_binding_contract.md", "1.0.0"),
    "docs/specs/execution_config_registry_contract.md": _extract_version("docs/specs/execution_config_registry_contract.md", "1.0.0"),

    "docs/specs/indexes/spec_catalog.md": _extract_version("docs/specs/indexes/spec_catalog.md", "1.0.0"),
    "docs/specs/indexes/spec_dependency_map.md": _extract_version("docs/specs/indexes/spec_dependency_map.md", "2.0.0"),
}
