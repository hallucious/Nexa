# Nexa Roadmap

---

# Phase 1 — Core Engine Stabilization + Runtime Durability Closure ✓ Complete

* DAG-based circuit execution
* Dependency-based node scheduling
* Artifact system (append-only, hashed)
* Execution trace (per-node, immutable)
* Provider abstraction (OpenAI, Anthropic, Gemini)
* Plugin system (restricted namespaces)
* Validation engine
* Contract-driven architecture

---

# Phase 2 — Observability and Determinism Tooling ✓ Complete

* Execution timeline, replay, determinism validator
* Artifact hashing, snapshot, diff
* Regression detector (typed reason codes, severity)
* Regression formatter and policy engine (PASS/WARN/FAIL)
* Audit pack, provenance graph, run comparator
* CLI: run, compare, diff, export, replay, info, and task commands
* Regression policy reason detail (trigger lines)

Current baseline: 1283 passed, 3 skipped

---

# Public GitHub Baseline (current)

* Official retained demo consolidated to `examples/real_ai_bug_autopsy_multinode/`
* Provider environment guidance unified across OpenAI, Codex, Claude, Gemini, and Perplexity
* Canonical public CLI clarified as `src.cli.nexa_cli:main`
* Legacy Nex compatibility is now wrapper-oriented: `src/engine/cli.py` is a bounded compatibility shim, `src/cli/savefile_runtime.py` owns execution dispatch, summary generation, payload emission, and baseline-policy wrapping, and `src/circuit/runtime_adapter.py` owns legacy preparation/adaptation logic
* Legacy `.nex` reverse-conversion / writer support removed; compatibility is execution-only
* Current repository baseline: 1283 passed, 3 skipped
* Role-aware `.nex` storage foundation started: `load_nex(...)`, `validate_working_save(...)`, `validate_commit_snapshot(...)`, and typed model split for `working_save` / `commit_snapshot`
* Storage lifecycle linkage started: Working Save → Commit Snapshot creation and Execution Record → Working Save last-run summary update APIs
* Pause/resume durability line now enforces commit-anchor, structure-fingerprint, execution-surface-fingerprint, and source-commit evidence presence before `resume_ready` may be true
* Replay-triggered runs are explicitly separated from resume-ready paused runs in storage/runtime summaries

---

# Phase 3 — CLI Regression Gating

Goal: Make regression policy actionable in CI/CD.

* `--baseline` flag for comparison run
* Exit code driven by PolicyDecision
* Configurable policy rules per-circuit or per-run

---

# Phase 4 — Developer Platform

* Configuration-driven policy rules
* Plugin versioning and marketplace
* CLI improvements and debugging dashboards

---

# Phase 5 — Circuit Builder

* Visual circuit editor
* Node configuration UI
* Runtime monitoring

---

# Long-Term

Nexa as a general-purpose runtime for AI computation systems — production pipelines, multi-agent systems, AI research infrastructure.

---

End of Roadmap


* legacy `.nex` plugin validation is owned by `src/platform/external_loader.py`; CLI keeps only branching, savefile fallback, and policy/output handling


- Legacy engine CLI compatibility is now fully wrapper-oriented: `src/engine/cli.py` is a bounded shim, `src/cli/savefile_runtime.py` owns execution dispatch, summary generation, payload emission, and baseline-policy wrapping, and `src/circuit/runtime_adapter.py` owns legacy preparation/adaptation logic.


- Execution record foundation implemented in code: contract, model, serialization, and working-save summary integration.


* Storage runtime linkage implemented in code: Commit Snapshot–anchored Execution Record creation and Working Save last-run update can now be driven from one lifecycle path
