# Contributing to Nexa

Project principles (priority order): reproducibility > contract stability > test proof > extensibility.

---

## 1. Terminology

- **Active spec**: enforced as a contract by the test suite
- **Source of Truth**: `docs/specs/_active_specs.yaml`
- **Spec-Version Sync**: doc `Version:` line must match `src/contracts/spec_versions.py`
- **FOUNDATION_MAP**: must reflect the active spec list exactly

---

## 2. Active Spec Change Procedure

**Step 1** — Update spec document, bump `Version:` line.

**Step 2** — Update `src/contracts/spec_versions.py` to match.

**Step 3** — If adding/removing a spec, update `docs/specs/_active_specs.yaml`.

**Step 4** — Update `docs/FOUNDATION_MAP.md` Active entries to match.

**Step 5** — Run contract tests:

```
pytest tests/test_spec_version_sync_contract.py
pytest tests/test_document_accumulation_contract.py
pytest tests/test_blueprint_foundation_sync_contract.py
pytest tests/test_foundation_autocheck_contract.py
```

All must pass before merging.

---

## 3. Code Contribution Rules

All pull requests must:

* pass `pytest` (full suite)
* respect all architectural invariants
* avoid breaking contracts
* include tests for new functionality
* not introduce system-level fixed pipeline execution

---

## 4. Non-Negotiable Architectural Invariants

1. Node is the only execution unit
2. System-level execution is dependency-based (no fixed global pipeline)
3. Node-internal pre/core/post phases are a node contract, not a system pipeline
4. Artifacts are append-only and immutable
5. Plugins write only to `plugin.<plugin_id>.*`
6. Execution must be deterministic
7. All behaviors governed by explicit contracts

---

## 5. Git Workflow

```bash
git checkout -b feature/my-feature
pytest
git add . && git commit -m "describe change"
git push origin feature/my-feature
# open pull request
```

---

End of Contributing Guide
