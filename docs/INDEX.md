# Nexa Documentation Index

---

# Quick Start (New Contributors)

1. `docs/README.md` — project overview
2. `docs/architecture/ARCHITECTURE.md` — system architecture
3. `docs/architecture/FOUNDATION_RULES.md` — non-negotiable invariants
4. `docs/CODING_PLAN.md` — completed steps and next targets
5. `docs/DEVELOPMENT.md` — environment setup and contribution process

---

# Root Documents

| File | Purpose |
|---|---|
| `docs/README.md` | Project overview |
| `docs/BLUEPRINT.md` | Architecture overview, active spec list, invariants |
| `docs/FOUNDATION_MAP.md` | Canonical doc index, Active/Partial/Planned status |
| `docs/CODING_PLAN.md` | Implementation history and next steps |
| `docs/ARCHITECTURE_CONSTITUTION.md` | Non-negotiable architectural principles |
| `docs/CONTRIBUTING.md` | Spec change procedure, PR requirements |
| `docs/DEVELOPMENT.md` | Environment setup, testing, contribution |
| `docs/GLOSSARY.md` | Terminology definitions |
| `docs/PLUGIN_SYSTEM.md` | Plugin architecture and contract |
| `docs/PROVIDER_SYSTEM.md` | Provider abstraction and contract |

---

# Architecture Documents (`docs/architecture/`)

| File | Purpose |
|---|---|
| `docs/architecture/ARCHITECTURE.md` | Full system architecture with execution model |
| `docs/architecture/FOUNDATION_RULES.md` | Korean-language architecture constitution |
| `docs/architecture/PROJECT_SCOPE.md` | Scope boundaries and MVP definition |

---

# Strategy Documents (`docs/strategy/`)

| File | Purpose |
|---|---|
| `docs/strategy/STRATEGY.md` | Product strategy and target market |
| `docs/strategy/VISION.md` | Long-term vision |
| `docs/strategy/ROADMAP.md` | Development phases and next steps |

---

# AI Tool Documents (`docs/ai/`)

| File | Purpose |
|---|---|
| `docs/ai/NEXA_FOR_AI.md` | Architecture guide for AI coding assistants |
| `docs/ai/CLAUDE_GUIDE.md` | Development rules for Claude |
| `docs/ai/CLAUDE_MASTER_PROMPT.md` | Master prompt for Claude coding sessions |

---

# Spec Documents (`docs/specs/`)

Active spec list: `docs/specs/_active_specs.yaml`

| Directory | Contents |
|---|---|
| `docs/specs/architecture/` | execution model, trace model, node contracts, circuit contract |
| `docs/specs/contracts/` | plugin, provider, prompt, validation, ExecutionConfig contracts |
| `docs/specs/policies/` | validation rule catalog and lifecycle |
| `docs/specs/foundation/` | terminology, architectural doctrine |
| `docs/specs/indexes/` | spec catalog and dependency map |
| `docs/specs/` (root) | ExecutionConfig binding and registry contracts |

---

# Contract Tests

```bash
pytest tests/test_spec_version_sync_contract.py        # spec versions match
pytest tests/test_document_accumulation_contract.py    # FM references exist
pytest tests/test_blueprint_foundation_sync_contract.py # FM == _active_specs.yaml
pytest tests/test_foundation_autocheck_contract.py     # FM and BLUEPRINT exist
```

---

End of Documentation Index
