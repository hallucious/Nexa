# Contributing to Nexa

Thanks for your interest in contributing to Nexa.

Nexa is a contract-driven AI execution engine. Contributions are welcome, but structural coherence matters more than speed. Small fixes can usually go straight to a PR. Changes that affect architecture, contracts, savefile behavior, provider behavior, or CLI behavior should be discussed in an issue or discussion before substantial implementation work begins.

Project priorities (highest first):

**inspectability > contract stability > test proof > extensibility**

---

## TL;DR

### For small changes
- Small docs fixes, typo fixes, and narrow bug fixes can usually go straight to a PR.
- Run `pytest -q` before opening the PR.
- If behavior changes, update tests.
- If docs become stale, update docs in the same PR.

### For architecture or contract changes
- Open an issue or discussion first.
- Update code, tests, and docs/specs together.
- Preserve all architectural invariants.
- Do not reintroduce fixed pipeline semantics or legacy slot-stage behavior.
- If active specs change, follow the active spec update procedure exactly.

---

## 1. Before You Start

This document is intentionally strict.

Nexa is not a loose collection of scripts. It is a contract-governed runtime with strong architectural constraints, and long-term maintainability depends on preserving those constraints. Read this document before making changes that affect execution behavior, specs, or public interfaces.

If you are new to the project, read in this order:

1. `README.md`
2. `docs/INDEX.md`
3. `docs/BLUEPRINT.md`
4. `docs/DEVELOPMENT.md`
5. `docs/PROVIDER_SYSTEM.md`

---

## 2. Local Development Setup

### Requirements

- Python 3.10+

### Basic setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### Validation

```bash
pytest -q
```

If you are modifying documentation-governed, contract-governed, or architecture-governed behavior, also read `docs/DEVELOPMENT.md` before opening a PR.

---

## 3. How to Propose Changes

### Small contributions

The following usually do **not** require pre-discussion:

- typo fixes
- small wording improvements in docs
- narrow bug fixes
- small tests that do not change architecture or contracts

### Larger contributions

Open an issue or discussion first for changes such as:

- architecture changes
- contract or schema changes
- savefile model changes
- provider lifecycle or provider contract changes
- CLI behavior changes
- large refactors
- anything affecting active specs or spec-governed behavior

Because Nexa has strong invariants, early discussion prevents wasted implementation effort.

If issue or pull request templates are available in the repository, please use them.

---

## 4. Terminology

- **Active spec**: a spec enforced as a contract by the test suite
- **Source of Truth**: `docs/specs/_active_specs.yaml`
- **Spec-Version Sync**: a spec document `Version:` line must match `src/contracts/spec_versions.py`
- **FOUNDATION_MAP**: must reflect the active spec list exactly
- **Savefile**: a runnable `.nex` artifact that may include circuit, state, resources, and UI-related data

---

## 5. Active Spec Change Procedure

**Step 1** — Update the spec document and bump its `Version:` line.

**Step 2** — Update `src/contracts/spec_versions.py` to match.

**Step 3** — If adding or removing a spec, update `docs/specs/_active_specs.yaml`.

**Step 4** — Update `docs/FOUNDATION_MAP.md` active entries to match.

**Step 5** — Run the contract tests:

```bash
pytest tests/test_spec_version_sync_contract.py
pytest tests/test_document_accumulation_contract.py
pytest tests/test_blueprint_foundation_sync_contract.py
pytest tests/test_foundation_autocheck_contract.py
```

All must pass before merging.

---

## 6. Code Contribution Rules

All pull requests must:

- pass `pytest -q` for the full suite
- preserve architectural invariants
- avoid breaking public or internal contracts without synchronized spec updates
- include tests for new behavior
- update docs/specs in the same change when behavior or contracts change
- avoid reintroducing fixed pipeline execution semantics
- avoid coupling core regression tests to disposable demos or examples

---

## 7. Core Architectural Invariants

These constraints exist to preserve architectural coherence and to prevent regressions into invalid legacy execution models.

1. **Node is the only execution unit.**
2. **System-level execution is dependency-based.** No fixed global pipeline is allowed.
3. **Node resources are prompt / provider / plugin references around a shared working context.** Depending on node role, any of these may be absent.
4. **Plugins are tools, not procedural stages.**
5. **Legacy slot-stage semantics are prohibited.** `pre_plugins`, `post_plugins`, and pre/core/post execution-stage models must not reappear as accepted architecture.
6. **Artifacts are append-only and immutable.**
7. **Plugins may write only inside `plugin.<plugin_id>.*`.**
8. **Determinism applies to scheduling, contract enforcement, and artifact integrity where defined.** Model outputs themselves may remain non-deterministic.
9. **Behavior must be governed by explicit contracts and tests.**

---

## 8. Documentation Sync Rules

When changing architecture, contracts, provider behavior, savefile behavior, or CLI surface:

- update the relevant docs in the same pull request
- remove stale descriptions rather than letting old behavior linger in docs
- keep `README.md`, `docs/INDEX.md`, and affected specs aligned with the current codebase

If a document no longer reflects reality, fix the document before treating the implementation as complete.

---

## 9. Example and Demo Rules

- The official retained demo is `examples/real_ai_bug_autopsy_multinode/`.
- Disposable example assets must not become hidden dependencies of the core regression suite.
- Demo-facing documentation must match the actual runnable paths and outputs.

---

## 10. Pull Request Checklist

Before opening a PR, confirm all of the following:

- [ ] `pytest -q` passes
- [ ] tests were added or updated for changed behavior
- [ ] docs/specs were updated when behavior or contracts changed
- [ ] fixed pipeline semantics were not reintroduced
- [ ] disposable demos did not become hidden test dependencies
- [ ] spec-version sync was updated if required

---

## 11. Git Workflow

```bash
git checkout -b feature/my-feature
pytest -q
git add .
git commit -m "describe change"
git push origin feature/my-feature
# open pull request
```

For spec-governed or doc-governed changes, include the relevant contract tests and documentation updates before opening the PR.

---

## 12. Final Note

Nexa welcomes contributions, but it is not a free-form repository.

Changes should make the system clearer, more inspectable, more contract-stable, and more trustworthy under change.
