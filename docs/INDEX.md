# Nexa Documentation Index

---

# Quick Start

1. `README.md` — public project overview and official demo entry
2. `docs/BLUEPRINT.md` — architecture overview, invariants, active spec list
3. `docs/architecture/ARCHITECTURE.md` — execution model and runtime structure
4. `docs/TRACKER.md` — implemented surface, completed milestones, next targets
5. `docs/DEVELOPMENT.md` — local setup, testing, and contributor workflow

---

# Root Documents

| File | Purpose |
|---|---|
| `README.md` | public overview, quick start, official retained demo |
| `docs/BLUEPRINT.md` | architecture overview, active spec list, invariants |
| `docs/TRACKER.md` | implementation tracker, release snapshot, next steps |
| `docs/ARCHITECTURE_CONSTITUTION.md` | non-negotiable architectural principles |
| `docs/CONTRIBUTING.md` | spec change procedure, PR requirements |
| `docs/DEVELOPMENT.md` | environment setup, testing, contributor workflow |
| `docs/GLOSSARY.md` | terminology definitions |
| `docs/PLUGIN_SYSTEM.md` | plugin architecture and contract |
| `docs/PROVIDER_SYSTEM.md` | provider implementation model and environment initialization |

---

# Architecture Documents (`docs/architecture/`)

| File | Purpose |
|---|---|
| `docs/architecture/ARCHITECTURE.md` | system architecture and execution flow |
| `docs/architecture/FOUNDATION_RULES.md` | architecture constitution / invariants |
| `docs/architecture/PROJECT_SCOPE.md` | scope boundaries and MVP / release scope |
| `docs/architecture/EXECUTION_RULES.md` | execution-level derived rules |

---

# Strategy Documents (`docs/strategy/`)

| File | Purpose |
|---|---|
| `docs/strategy/STRATEGY.md` | product strategy and target market |
| `docs/strategy/VISION.md` | long-term vision |
| `docs/strategy/ROADMAP.md` | completed phases, public baseline, next phases |

---

# AI Tool Documents (`docs/ai/`)

| File | Purpose |
|---|---|
| `docs/ai/NEXA_FOR_AI.md` | architecture guide for AI coding assistants |
| `docs/ai/CLAUDE_GUIDE.md` | development rules for Claude |
| `docs/ai/CLAUDE_MASTER_PROMPT.md` | master prompt for Claude coding sessions |

---

# Spec Documents (`docs/specs/`)

Active contract/version registry: `src/contracts/spec_version_registry.py`

| Directory | Contents |
|---|---|
| `docs/specs/architecture/` | execution model, trace model, node contracts, circuit contract |
| `docs/specs/contracts/` | plugin, provider, prompt, validation, ExecutionConfig contracts |
| `docs/specs/policies/` | validation rule catalog and lifecycle |
| `docs/specs/foundation/` | terminology and architectural doctrine |
| `docs/specs/indexes/` | spec catalog and dependency map |
| `docs/specs/` (root) | ExecutionConfig binding and registry contracts |

---
# UI / Editor Reference Set (`docs/specs/ui/`)

These documents define the replaceable UI shell, module view-model contracts, UI-owned state rules, and `.nex.ui` boundaries. They are currently **supporting reference specs**, not part of the YAML-backed active spec core.

| Directory / File | Purpose |
|---|---|
| `docs/specs/ui/ui_architecture_package.md` | overall UI architecture position and module-slot system |
| `docs/specs/ui/ui_adapter_view_model_contract.md` | canonical engine ↔ UI adapter boundary |
| `docs/specs/ui/*_view_model_spec.md` | module-level view-model contracts for Graph / Inspector / Validation / Execution / Designer / Trace / Artifact / Storage / Diff |
| `docs/specs/ui/theme_layout_layer_spec.md` | outer visual layer rules |
| `docs/specs/ui/ui_state_ownership_and_persistence_spec.md` | UI-owned state boundary |
| `docs/specs/ui/ui_section_schema_spec.md` | `.nex.ui` schema |
| `docs/specs/ui/ui_section_branch_rules_spec.md` | role-aware handling of `.nex.ui` |
| `docs/specs/ui/ui_public_api_exposure_spec.md` | public API exposure rules for `.nex.ui` |
| `docs/specs/ui/ui_commit_boundary_stripping_spec.md` | commit-boundary stripping of UI-owned state |
| `docs/specs/ui/ui_typed_model_binding_spec.md` | UI typed-model binding rules |
| `docs/specs/ui/ui_workflow_collaboration_protocol.md` | UI collaboration / workflow protocol |

## UI Internationalization Reference Bundle

These new documents define multilingual UI behavior as a **UI-owned supporting reference set**. They must not be treated as engine-owned truth.

| File | Purpose |
|---|---|
| `docs/specs/ui/ui_i18n_spec_index.md` | canonical index for the UI i18n document bundle |
| `docs/specs/ui/ui_i18n_bundle_manifest.md` | bundle manifest and placement guide |
| `docs/specs/ui/ui_multilingual_localization_architecture.md` | top-level multilingual architecture |
| `docs/specs/ui/ui_language_settings_contract.md` | app language / AI response language / format locale contract |
| `docs/specs/ui/i18n_resource_schema_spec.md` | translation resource bundle structure |
| `docs/specs/ui/ui_i18n_fallback_behavior_spec.md` | deterministic fallback resolution rules |
| `docs/specs/ui/localized_message_resolution_spec.md` | localized message lookup and rendering path |
| `docs/specs/ui/validation_reason_code_localization_spec.md` | reason_code → localized validation message mapping |
| `docs/specs/ui/ai_response_language_policy_spec.md` | AI response language policy separate from UI language |
| `docs/specs/ui/ui_i18n_persistence_boundary_spec.md` | i18n persistence boundary within UI-owned state |
| `docs/specs/ui/localization_test_strategy_spec.md` | localization regression and coverage strategy |

**Important:** the active contract/version registry is intentionally **not** updated by this bundle because these i18n documents are not yet part of the code-synchronized active contract set.

---

# Current Public Release Notes

- The repository keeps one official demo: `examples/real_ai_bug_autopsy_multinode/`
- Provider environment guidance is implemented across OpenAI, Codex, Claude, Gemini, and Perplexity
- Current broad full-suite anchor: `2576 passed, 14 skipped`
- Current restore-point commit: `1175d72`
- Current post-anchor note: `1175d72` only removed references to two intentionally deleted status documents

---

End of Documentation Index


---

# Storage / Format References

These documents are currently the main supporting references for the role-aware storage direction and three-layer lifecycle:

| File | Purpose |
|---|---|
| `docs/specs/storage/storage_architecture_overview.md` | three-layer storage overview |
| `docs/specs/storage/storage_lifecycle_spec.md` | save / commit / execute lifecycle |
| `docs/specs/storage/working_save_spec.md` | editable present-state layer |
| `docs/specs/storage/commit_snapshot_spec.md` | approval-gated structural anchor |
| `docs/specs/storage/execution_record_spec.md` | run-scoped historical artifact |
| `docs/specs/storage/storage_format_mapping_spec.md` | lifecycle-to-format mapping |
| `docs/specs/formats/nex_unified_schema.md` | unified `.nex` family schema |
| `docs/specs/formats/nex_parser_validator_branch_rules.md` | role-aware load/validate branching |
| `docs/specs/formats/nex_typed_model_spec.md` | typed model split for `.nex` roles |
| `docs/specs/formats/nex_load_validate_api_spec.md` | public `.nex` load / validate API shape |
