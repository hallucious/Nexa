# FOUNDATION_MAP

Version: 1.6.0

## Purpose

This document defines the canonical documentation map of the Nexa repository.

It serves two roles:

1. document navigation for core architectural materials
2. synchronization reference for the active spec set declared in `docs/specs/_active_specs.yaml`

## Principles

- 유효한 내용은 유지한다.
- obsolete or conflicting content is 삭제 대상이다.
- deprecation is allowed only as an explicit transition decision, not as silent drift.
- the active spec set in `docs/specs/_active_specs.yaml` and the Active rows below MUST remain identical.

---

## Core Documents

| Document | Path | Status | Description |
|---|---|---|---|
| blueprint | docs/BLUEPRINT.md | Active | top-level project reference |
| architecture_constitution | docs/ARCHITECTURE_CONSTITUTION.md | Active | highest architectural invariants |
| execution_rules | docs/architecture/EXECUTION_RULES.md | Active | derived execution rules |
| tracker | docs/TRACKER.md | Active | implementation tracker, release snapshot, and next steps |
| development | docs/DEVELOPMENT.md | Active | development workflow |
| current_state | docs/status/CURRENT_STATE.md | Supporting | repository status snapshot and sector truth matrix |
| current_implementation_state | docs/status/CURRENT_IMPLEMENTATION_STATE.md | Supporting | short-form implementation truth sheet |

---

## Active Specifications

Source of Truth:
`docs/specs/_active_specs.yaml`

The following rows marked Active MUST match the YAML list exactly.

| Spec | Path | Status | Category |
|---|---|---|---|
| terminology | docs/specs/foundation/terminology.md | Active | foundation |
| execution_model | docs/specs/architecture/execution_model.md | Active | architecture |
| trace_model | docs/specs/architecture/trace_model.md | Active | architecture |
| node_abstraction | docs/specs/architecture/node_abstraction.md | Active | architecture |
| node_execution_contract | docs/specs/architecture/node_execution_contract.md | Active | architecture |
| circuit_contract | docs/specs/architecture/circuit_contract.md | Active | architecture |
| universal_provider_architecture | docs/specs/architecture/universal_provider_architecture.md | Active | architecture |
| execution_environment_contract | docs/specs/contracts/execution_environment_contract.md | Active | contracts |
| plugin_contract | docs/specs/contracts/plugin_contract.md | Active | contracts |
| plugin_registry_contract | docs/specs/contracts/plugin_registry_contract.md | Active | contracts |
| prompt_contract | docs/specs/contracts/prompt_contract.md | Active | contracts |
| provider_contract | docs/specs/contracts/provider_contract.md | Active | contracts |
| validation_engine_contract | docs/specs/contracts/validation_engine_contract.md | Active | contracts |
| execution_config_canonicalization_contract | docs/specs/contracts/execution_config_canonicalization_contract.md | Active | contracts |
| execution_config_schema_contract | docs/specs/contracts/execution_config_schema_contract.md | Active | contracts |
| context_key_schema_contract | docs/specs/contracts/context_key_schema_contract.md | Active | contracts |
| validation_rule_catalog | docs/specs/policies/validation_rule_catalog.md | Active | policies |
| validation_rule_lifecycle | docs/specs/policies/validation_rule_lifecycle.md | Active | policies |
| spec_catalog | docs/specs/indexes/spec_catalog.md | Active | indexes |
| spec_dependency_map | docs/specs/indexes/spec_dependency_map.md | Active | indexes |
| execution_config_prompt_binding_contract | docs/specs/execution_config_prompt_binding_contract.md | Active | execution_config |
| execution_config_registry_contract | docs/specs/execution_config_registry_contract.md | Active | execution_config |

---

## Related Index Documents

- `docs/specs/indexes/spec_catalog.md`
- `docs/specs/indexes/spec_dependency_map.md`

## Governance Notes

- If a valid document still reflects current code and contract behavior, it remains active.
- If a document becomes obsolete or contradictory, it must be deleted or explicitly replaced.
- Silent divergence between docs, specs, and code is forbidden.


---

## Supporting Storage / Format References

The following storage and format documents are currently supporting references for the role-aware `.nex` direction and three-layer storage lifecycle.
They are not part of the active spec YAML set yet, but they are valid supporting design references for storage-sector sync work.

| Spec | Path | Status | Category |
|---|---|---|---|
| storage_architecture_overview | docs/specs/storage/storage_architecture_overview.md | Supporting | storage |
| storage_lifecycle_spec | docs/specs/storage/storage_lifecycle_spec.md | Supporting | storage |
| working_save_spec | docs/specs/storage/working_save_spec.md | Supporting | storage |
| commit_snapshot_spec | docs/specs/storage/commit_snapshot_spec.md | Supporting | storage |
| execution_record_spec | docs/specs/storage/execution_record_spec.md | Supporting | storage |
| storage_format_mapping_spec | docs/specs/storage/storage_format_mapping_spec.md | Supporting | storage |
| nex_unified_schema | docs/specs/formats/nex_unified_schema.md | Supporting | formats |
| nex_parser_validator_branch_rules | docs/specs/formats/nex_parser_validator_branch_rules.md | Supporting | formats |
| nex_typed_model_spec | docs/specs/formats/nex_typed_model_spec.md | Supporting | formats |
| nex_load_validate_api_spec | docs/specs/formats/nex_load_validate_api_spec.md | Supporting | formats |


## Precision Documentation Governance

- Precision concepts are valid, but they must live in existing best-fit architectural / contract / storage / designer documents.
- A standalone `docs/specs/precision/` sector is not the long-term canonical documentation shape.
- When precision semantics evolve, update the existing source-of-truth documents rather than reintroducing a separate precision namespace.


## Precision Closeout Status

- Precision-era foundations should now be treated as converged into the canonical engine / contract / storage / designer documents.
- New work in this area should prefer cleanup, deduplication, and stronger contract tests over additional precision-branded subsystems.
- Do not recreate a standalone precision documentation sector.
