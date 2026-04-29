from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SpecVersionEntry:
    spec_id: str
    path: str
    version: str
    family: str = "plugins"


_PLUGIN_BUILDER_SPEC_VERSION_ENTRIES: tuple[SpecVersionEntry, ...] = (
    SpecVersionEntry("plugin_builder_spec_contract", "docs/specs/plugins/plugin_builder_spec_contract.md", "1.0"),
    SpecVersionEntry("designer_to_plugin_builder_intake_contract", "docs/specs/plugins/designer_to_plugin_builder_intake_contract.md", "1.0"),
    SpecVersionEntry("plugin_namespace_policy_contract", "docs/specs/plugins/plugin_namespace_policy_contract.md", "1.0"),
    SpecVersionEntry("plugin_runtime_artifact_manifest_contract", "docs/specs/plugins/plugin_runtime_artifact_manifest_contract.md", "1.0"),
    SpecVersionEntry("plugin_registry_contract", "docs/specs/plugins/plugin_registry_contract.md", "1.0"),
    SpecVersionEntry("plugin_verification_test_policy_contract", "docs/specs/plugins/plugin_verification_test_policy_contract.md", "1.0"),
    SpecVersionEntry("plugin_runtime_loading_installation_contract", "docs/specs/plugins/plugin_runtime_loading_installation_contract.md", "1.0"),
    SpecVersionEntry("plugin_runtime_execution_binding_contract", "docs/specs/plugins/plugin_runtime_execution_binding_contract.md", "1.0"),
    SpecVersionEntry("plugin_context_io_contract", "docs/specs/plugins/plugin_context_io_contract.md", "1.0"),
    SpecVersionEntry("plugin_failure_recovery_contract", "docs/specs/plugins/plugin_failure_recovery_contract.md", "1.0"),
    SpecVersionEntry("plugin_runtime_observability_contract", "docs/specs/plugins/plugin_runtime_observability_contract.md", "1.0"),
    SpecVersionEntry("plugin_runtime_governance_contract", "docs/specs/plugins/plugin_runtime_governance_contract.md", "1.0"),
    SpecVersionEntry("plugin_lifecycle_state_machine_contract", "docs/specs/plugins/plugin_lifecycle_state_machine_contract.md", "1.0"),
    SpecVersionEntry("plugin_classification_mcp_compatibility_contract", "docs/specs/plugins/plugin_classification_mcp_compatibility_contract.md", "1.0"),
    SpecVersionEntry("plugin_contract_family_index", "docs/specs/plugins/plugin_contract_family_index.md", "1.0"),
)


def plugin_builder_spec_versions() -> tuple[SpecVersionEntry, ...]:
    return _PLUGIN_BUILDER_SPEC_VERSION_ENTRIES


def spec_version_by_id(spec_id: str) -> SpecVersionEntry | None:
    normalized = str(spec_id or "").strip()
    for entry in _PLUGIN_BUILDER_SPEC_VERSION_ENTRIES:
        if entry.spec_id == normalized:
            return entry
    return None


def assert_unique_spec_ids(entries: Iterable[SpecVersionEntry]) -> None:
    ids = [entry.spec_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate spec ids are not allowed")


__all__ = [
    "SpecVersionEntry",
    "assert_unique_spec_ids",
    "plugin_builder_spec_versions",
    "spec_version_by_id",
]
