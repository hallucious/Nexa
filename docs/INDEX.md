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
| `docs/FOUNDATION_MAP.md` | canonical doc index, Active/Partial/Planned status |
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

Active spec list: `docs/specs/_active_specs.yaml`

| Directory | Contents |
|---|---|
| `docs/specs/architecture/` | execution model, trace model, node contracts, circuit contract |
| `docs/specs/contracts/` | plugin, provider, prompt, validation, ExecutionConfig contracts |
| `docs/specs/policies/` | validation rule catalog and lifecycle |
| `docs/specs/foundation/` | terminology and architectural doctrine |
| `docs/specs/indexes/` | spec catalog and dependency map |
| `docs/specs/` (root) | ExecutionConfig binding and registry contracts |

---

# Current Public Release Notes

- The repository keeps one official demo: `examples/real_ai_bug_autopsy_multinode/`
- Provider environment guidance is implemented across OpenAI, Codex, Claude, Gemini, and Perplexity
- Current verified baseline: `1027 passed, 3 skipped`

---

# Contract Tests

```bash
pytest tests/test_spec_version_sync_contract.py
pytest tests/test_document_accumulation_contract.py
pytest tests/test_blueprint_foundation_sync_contract.py
pytest tests/test_foundation_autocheck_contract.py
```

---

End of Documentation Index
