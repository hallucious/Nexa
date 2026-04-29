from __future__ import annotations

import json

from src.contracts.spec_versions import assert_unique_spec_ids, plugin_builder_spec_versions, spec_version_by_id
from src.plugins.contracts.builder_types import (
    PluginBuilderSpec,
    PluginInputContract,
    PluginOutputContract,
)
from src.plugins.contracts.serialization import dataclass_from_payload, dataclass_to_payload


def test_plugin_builder_spec_versions_register_contract_family() -> None:
    entries = plugin_builder_spec_versions()

    assert len(entries) == 15
    assert spec_version_by_id("plugin_builder_spec_contract") is not None
    assert spec_version_by_id("plugin_contract_family_index") is not None
    assert all(entry.path.startswith("docs/specs/plugins/") for entry in entries)
    assert_unique_spec_ids(entries)


def test_plugin_builder_spec_payload_round_trip_preserves_nested_contracts() -> None:
    spec = PluginBuilderSpec(
        spec_version="plugin-builder-spec.v1",
        plugin_purpose="Summarize uploaded contract clauses.",
        plugin_name_hint="contract_clause_summarizer",
        plugin_category="document_analysis",
        capability_summary="Extract and summarize contract clauses.",
        input_contract=PluginInputContract(fields={"document_text": {"type": "string"}}, summary="Document text"),
        output_contract=PluginOutputContract(fields={"clauses": {"type": "list"}}, summary="Clause list"),
    )

    payload = dataclass_to_payload(spec)
    serialized = json.dumps(payload, sort_keys=True)

    assert "contract_clause_summarizer" in serialized
    assert payload["input_contract"]["fields"]["document_text"]["type"] == "string"
    restored = dataclass_from_payload(PluginBuilderSpec, payload)
    assert restored.plugin_purpose == spec.plugin_purpose
    assert restored.input_contract.fields == spec.input_contract.fields
