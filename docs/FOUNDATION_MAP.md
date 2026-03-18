# FOUNDATION_MAP

Version: 1.4.1

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
| coding_plan | docs/CODING_PLAN.md | Active | implementation status and next steps |
| readme | docs/README.md | Active | repository entry document |
| development | docs/DEVELOPMENT.md | Active | development workflow |

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
