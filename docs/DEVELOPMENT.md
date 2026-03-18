# Nexa Development Guide

Before modifying code, read:
* `docs/architecture/ARCHITECTURE.md`
* `docs/architecture/FOUNDATION_RULES.md`
* `docs/CODING_PLAN.md`

---

# Development Environment

Language: Python 3.11+

```bash
pip install -r requirements.txt
python -m venv .venv && source .venv/bin/activate
```

---

# Running Tests

```bash
python -m pytest        # full suite
pytest -q               # quick run
```

All tests must pass. Never ignore failures.

---

# Test Categories

**Unit Tests** — component-level verification

**Contract Tests** — spec-version sync, document accumulation, foundation map consistency

**Runtime Tests** — execution behavior verification

**Regression Tests** — prevent previously fixed bugs

Contract tests are critical — they enforce doc/code/architecture alignment.

---

# Repository Structure

```
src/
    artifacts/      engine/         platform/
    circuit/        models/         policy/
    cli/            prompts/        providers/
    config/         utils/
    contracts/

docs/
    BLUEPRINT.md            FOUNDATION_MAP.md
    CODING_PLAN.md          CONTRIBUTING.md
    DEVELOPMENT.md          GLOSSARY.md  INDEX.md
    architecture/           strategy/           ai/
    specs/                  (all active specs)

tests/
examples/
scripts/    tools/
```

---

# Spec-Version Synchronization

Every active spec in `docs/specs/_active_specs.yaml` must:
1. Exist at that path
2. Have a `Version: X.Y.Z` header
3. Match the version in `src/contracts/spec_versions.py`

Verify:
```bash
pytest tests/test_spec_version_sync_contract.py
```

---

# Architectural Constraints

**Node is the only execution unit.**

**System-level execution is dependency-based.** No fixed global ordering.

**Node-internal pre/core/post phases are a node contract.** Not a system pipeline.

**Artifacts are append-only.** Never modify existing artifacts.

**Plugins write only to `plugin.<plugin_id>.*`.**

---

# Code Style

```bash
black src
ruff check src
```

---

# Pull Request Requirements

* Full test suite passes
* Respects architectural invariants
* Does not break contracts
* Includes tests for new functionality

---

End of Development Guide
