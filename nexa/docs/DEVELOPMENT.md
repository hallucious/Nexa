# Nexa Development Guide

# Authority Order

1. `docs/ARCHITECTURE_CONSTITUTION.md`
2. `docs/architecture/EXECUTION_RULES.md`
3. Active specs in `docs/specs/`
4. Code

Lower layers must comply with upper layers.

---

Before modifying code, read:

* `docs/ARCHITECTURE_CONSTITUTION.md`
* `docs/architecture/ARCHITECTURE.md`
* `docs/architecture/EXECUTION_RULES.md`
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

**Contract Tests** — spec-version sync, document accumulation, blueprint/spec consistency

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
    README.md                   ARCHITECTURE_CONSTITUTION.md
    BLUEPRINT.md                CODING_PLAN.md
    DEVELOPMENT.md              GLOSSARY.md
    architecture/               strategy/               ai/
    specs/                      (all active specs only)

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

# Contribution Rules

Project principles (priority order):

reproducibility > contract stability > test proof > extensibility

All pull requests must:

* pass `pytest` (full suite)
* respect all architectural invariants
* avoid breaking contracts
* include tests for new functionality
* not introduce system-level fixed pipeline execution

---

# Active Spec Change Procedure

**Step 1** — Update the spec document and bump the `Version:` line.

**Step 2** — Update `src/contracts/spec_versions.py` to match.

**Step 3** — If adding or removing a spec, update `docs/specs/_active_specs.yaml`.

**Step 4** — Update any derived indexes or references that depend on the active spec set.

**Step 5** — Run contract tests:

```bash
pytest tests/test_spec_version_sync_contract.py
pytest tests/test_document_accumulation_contract.py
pytest tests/test_blueprint_foundation_sync_contract.py
pytest tests/test_foundation_autocheck_contract.py
```

All must pass before merging.

---

# Architectural Constraints

**Node is the only execution unit.**

**System-level execution is dependency-based.** No fixed global ordering.

**Node-internal pre/core/post phases are a node contract.** Not a system pipeline.

**Artifacts are append-only.** Never modify existing artifacts.

**Plugins write only to `plugin.<plugin_id>.*`.**

**Execution must be deterministic.**

---

# Code Style

```bash
black src
ruff check src
```

---

# Git Workflow

```bash
git checkout -b feature/my-feature
pytest
git add .
git commit -m "describe change"
git push origin feature/my-feature
# open pull request
```

---

End of Development Guide
